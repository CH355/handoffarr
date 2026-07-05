"""Automated production validation checks.

Pure helpers that read the current persisted lifecycle state and assert that
the interpreters agree with each other. Each check returns one of:

- ``OK``    — the assertion holds.
- ``WARN``  — the assertion is satisfied vacuously (no data).
- ``FAIL``  — the assertion is violated; this is a production-level signal.

The checks intentionally do not call collectors or external services; they
only inspect persisted state so they are safe to run from the dashboard.
"""

from __future__ import annotations

from typing import Any

from . import db
from .cleanup import (
    CLEANUP_FAILED,
    CLEANUP_PENDING,
    CLEANUP_UNKNOWN,
)
from .cleanup_reconciliation import (
    latest_completed_execution_index,
    matching_completed_execution,
)
from .cleanup_review import RISKY_REVIEW, SAFE_REVIEW, build_cleanup_review
from .config import Config
from .imports import IMPORT_SUCCESS
from .library import (
    LIBRARY_MISSING,
    LIBRARY_PRESENT,
    enrich_library_artifacts,
)
from .perf import timed, trace

OK = "OK"
WARN = "WARN"
FAIL = "FAIL"


def _check(name: str, status: str, reason: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "reason": reason,
        "evidence": evidence or {},
    }


def validate_imports(import_events: list[dict[str, Any]], artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    """Import successes must produce at least one Library Present artefact."""
    import_success_count = sum(
        1 for e in import_events if e.get("import_status") == IMPORT_SUCCESS
    )
    library_present_count = sum(
        1 for a in artifacts if a.get("library_status") == LIBRARY_PRESENT
    )
    if import_success_count == 0:
        return _check(
            "Import Validation",
            WARN,
            "No Import Success events observed.",
            {"import_success": 0},
        )
    if library_present_count == 0:
        return _check(
            "Import Validation",
            FAIL,
            "Import Success events exist but no Library Present artefacts.",
            {
                "import_success": import_success_count,
                "library_present": 0,
            },
        )
    return _check(
        "Import Validation",
        OK,
        f"{import_success_count} import success; {library_present_count} library present.",
        {
            "import_success": import_success_count,
            "library_present": library_present_count,
        },
    )


def validate_library(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    """An artefact whose mapped path exists must not be classified Missing."""
    offenders: list[dict[str, Any]] = []
    for artifact in artifacts:
        if artifact.get("library_status") != LIBRARY_MISSING:
            continue
        evidence = artifact.get("evidence") or {}
        if evidence.get("path_verified") is True or artifact.get("file_exists"):
            offenders.append(
                {
                    "media_id": artifact.get("media_id"),
                    "media_title": artifact.get("media_title"),
                    "library_path": artifact.get("library_path"),
                }
            )
    if offenders:
        return _check(
            "Library Validation",
            FAIL,
            "Files exist on disk but artefact classified Library Missing.",
            {"offenders": offenders[:10], "count": len(offenders)},
        )
    if not artifacts:
        return _check(
            "Library Validation",
            WARN,
            "No library artefacts observed.",
        )
    return _check(
        "Library Validation",
        OK,
        f"{len(artifacts)} library artefact(s) consistent with mapped paths.",
    )


def validate_cleanup(
    artifacts: list[dict[str, Any]],
    cleanup_events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Library Present + download copy present must produce a known cleanup status."""
    cleanup_by_media = {
        str(event.get("media_id")): event for event in cleanup_events
    }
    offenders: list[dict[str, Any]] = []
    for artifact in artifacts:
        if artifact.get("library_status") != LIBRARY_PRESENT:
            continue
        if artifact.get("import_status") != IMPORT_SUCCESS:
            continue
        if not artifact.get("download_copy_present"):
            continue
        media_id = str(artifact.get("media_id") or "")
        cleanup = cleanup_by_media.get(media_id)
        status = cleanup.get("cleanup_status") if cleanup else CLEANUP_UNKNOWN
        if status == CLEANUP_UNKNOWN or status is None:
            offenders.append(
                {
                    "media_id": media_id,
                    "media_title": artifact.get("media_title"),
                    "cleanup_status": status,
                }
            )
    if offenders:
        return _check(
            "Cleanup Validation",
            FAIL,
            "Library + download copy both present but cleanup status is Unknown.",
            {"offenders": offenders[:10], "count": len(offenders)},
        )
    return _check(
        "Cleanup Validation",
        OK,
        "All library/download overlaps have a known cleanup status.",
    )


def validate_recommendations(
    cleanup_events: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Recoverable bytes > 0 must produce at least one cleanup recommendation."""
    recoverable_bytes = sum(
        int(event.get("recoverable_bytes") or 0)
        for event in cleanup_events
        if event.get("cleanup_status") in {CLEANUP_PENDING, CLEANUP_FAILED}
    )
    if recoverable_bytes <= 0:
        return _check(
            "Recommendations Validation",
            OK,
            "Nothing recoverable; no recommendation required.",
            {"recoverable_bytes": 0},
        )
    has_storage_rec = any(
        str(rec.get("category")) in {"Storage Recovery", "Cleanup Policy"}
        for rec in recommendations
    )
    if not has_storage_rec:
        return _check(
            "Recommendations Validation",
            FAIL,
            "Recoverable bytes detected but no storage recommendation emitted.",
            {"recoverable_bytes": recoverable_bytes},
        )
    return _check(
        "Recommendations Validation",
        OK,
        "Recoverable bytes covered by a storage recommendation.",
        {"recoverable_bytes": recoverable_bytes},
    )


def validate_completed_execution_reconciliation(
    config: Config,
    cleanup_events: list[dict[str, Any]],
    import_events: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
    traces: list[dict[str, Any]],
    executions: list[dict[str, Any]],
    review_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    completed_index = latest_completed_execution_index(executions)
    completed_hashes = set((completed_index.get("by_hash") or {}).keys())
    if not completed_hashes:
        return _check(
            "Cleanup Execution Reconciliation",
            OK,
            "No completed cleanup executions require reconciliation.",
        )

    if review_items is None:
        review_items = build_cleanup_review(
            cleanup_events,
            import_events,
            artifacts,
            traces,
            config,
        )
    offenders: list[dict[str, Any]] = []
    for item in review_items:
        if item.get("review_class") not in {SAFE_REVIEW, RISKY_REVIEW}:
            continue
        matched = matching_completed_execution(item, completed_index)
        if not matched:
            continue
        offenders.append(
            {
                "media_id": item.get("media_id"),
                "media_title": item.get("media_title"),
                "qbit_hash": item.get("qbit_hash") or item.get("torrent_hash"),
                "review_class": item.get("review_class"),
                "recoverable_bytes": item.get("recoverable_bytes"),
                "execution_id": matched.get("execution_id"),
            }
        )
    if offenders:
        return _check(
            "Cleanup Execution Reconciliation",
            FAIL,
            "Completed cleanup execution still appears as a Safe or Risky cleanup review candidate.",
            {"offenders": offenders[:10], "count": len(offenders)},
        )
    return _check(
        "Cleanup Execution Reconciliation",
        OK,
        "Completed cleanup executions are excluded from Safe and Risky review candidates.",
        {"completed_execution_hashes": len(completed_hashes)},
    )


def validate_batch_execution_safety(
    config: Config,
    batches: list[dict[str, Any]],
) -> dict[str, Any]:
    cfg = config.section("cleanup_execution")
    allowed_strengths = set(
        cfg.get(
            "allowed_match_strengths",
            [
                "Exact Hash/DownloadId Match",
                "Exact Library Path Match",
                "Filename + Size Match",
            ],
        )
    )
    offenders: list[dict[str, Any]] = []
    checked = 0
    for batch in batches:
        evidence = batch.get("evidence") or {}
        items = evidence.get("items") if isinstance(evidence.get("items"), list) else []
        if not items:
            continue
        checked += 1
        planned_total = int(batch.get("planned_recoverable_bytes") or 0)
        item_total = sum(int(item.get("recoverable_bytes") or 0) for item in items)
        if planned_total != item_total:
            offenders.append(
                {
                    "batch_id": batch.get("batch_id"),
                    "reason": "Batch planned recoverable bytes do not equal per-item sum.",
                    "planned_recoverable_bytes": planned_total,
                    "per_item_sum": item_total,
                }
            )
        for item in items:
            if item.get("review_class") != SAFE_REVIEW:
                offenders.append(
                    {
                        "batch_id": batch.get("batch_id"),
                        "media_id": item.get("media_id"),
                        "reason": "Batch plan includes a non-safe review candidate.",
                        "review_class": item.get("review_class"),
                    }
                )
            if item.get("match_strength") not in allowed_strengths:
                offenders.append(
                    {
                        "batch_id": batch.get("batch_id"),
                        "media_id": item.get("media_id"),
                        "reason": "Batch plan includes a disallowed match strength.",
                        "match_strength": item.get("match_strength"),
                    }
                )
    if offenders:
        return _check(
            "Cleanup Batch Safety",
            FAIL,
            "One or more cleanup batch plans violate execution safety rules.",
            {"offenders": offenders[:10], "count": len(offenders)},
        )
    gate = (
        "enabled"
        if cfg.get("enabled") and cfg.get("allow_batch_execution")
        else "closed"
    )
    return _check(
        "Cleanup Batch Safety",
        OK,
        "Batch plans are limited to safe candidates and allowed match strengths.",
        {"checked_batches": checked, "batch_execution_gate": gate},
    )


def run_validation(
    config: Config,
    *,
    artifacts: list[dict[str, Any]] | None = None,
    review_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run every validation check against the current persisted state."""
    with timed("validation_db_read", table="import_events"):
        import_events = db.all_import_events()
    if artifacts is None:
        with timed("validation_db_read", table="library_artifacts"):
            library_artifacts = db.all_library_artifacts()
        with timed("validation_library_enrichment", artifacts=len(library_artifacts)):
            artifacts = enrich_library_artifacts(library_artifacts, config)
    with timed("validation_db_read", table="cleanup_events"):
        cleanup_events = db.all_cleanup_events()
    with timed("validation_db_read", table="recommendations"):
        recommendations = db.all_recommendations()
    with timed("validation_db_read", table="cleanup_executions", limit=5000):
        executions = db.all_cleanup_executions(limit=5000)
    with timed("validation_db_read", table="cleanup_execution_batches", limit=5000):
        batches = db.all_cleanup_execution_batches(limit=5000)
    with timed("validation_completed_execution_index", executions=len(executions)):
        completed_index = latest_completed_execution_index(executions)
    with timed("validation_recommendation_cleanup_filter", cleanup_events=len(cleanup_events)):
        recommendation_cleanup_events = [
            event
            for event in cleanup_events
            if not matching_completed_execution(event, completed_index)
        ]

    checks = []
    with timed("validation_check", check="imports", import_events=len(import_events), artifacts=len(artifacts)):
        checks.append(validate_imports(import_events, artifacts))
    with timed("validation_check", check="library", artifacts=len(artifacts)):
        checks.append(validate_library(artifacts))
    with timed("validation_check", check="cleanup", artifacts=len(artifacts), cleanup_events=len(cleanup_events)):
        checks.append(validate_cleanup(artifacts, cleanup_events))
    with timed("validation_check", check="recommendations", cleanup_events=len(recommendation_cleanup_events), recommendations=len(recommendations)):
        checks.append(validate_recommendations(recommendation_cleanup_events, recommendations))
    with timed("validation_db_read", table="handoff_traces"):
        traces = db.all_traces()
    with timed(
        "validation_check",
        check="completed_execution_reconciliation",
        cleanup_events=len(cleanup_events),
        import_events=len(import_events),
        artifacts=len(artifacts),
        traces=len(traces),
        executions=len(executions),
        review_items="provided" if review_items is not None else "generated",
    ):
        checks.append(
            validate_completed_execution_reconciliation(
                config,
                cleanup_events,
                import_events,
                artifacts,
                traces,
                executions,
                review_items=review_items,
            )
        )
    with timed("validation_check", check="batch_execution_safety", batches=len(batches)):
        checks.append(validate_batch_execution_safety(config, batches))
    overall = OK
    if any(c["status"] == FAIL for c in checks):
        overall = FAIL
    elif any(c["status"] == WARN for c in checks):
        overall = WARN
    trace(
        "validation_response",
        status=overall,
        checks=len(checks),
        import_events=len(import_events),
        artifacts=len(artifacts),
        cleanup_events=len(cleanup_events),
        recommendations=len(recommendations),
        executions=len(executions),
        batches=len(batches),
    )
    return {"status": overall, "checks": checks}
