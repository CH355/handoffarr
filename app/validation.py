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
from .config import Config
from .imports import IMPORT_SUCCESS
from .library import (
    LIBRARY_MISSING,
    LIBRARY_PRESENT,
    enrich_library_artifacts,
)

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


def run_validation(config: Config) -> dict[str, Any]:
    """Run every validation check against the current persisted state."""
    import_events = db.all_import_events()
    artifacts = enrich_library_artifacts(db.all_library_artifacts(), config)
    cleanup_events = db.all_cleanup_events()
    recommendations = db.all_recommendations()

    checks = [
        validate_imports(import_events, artifacts),
        validate_library(artifacts),
        validate_cleanup(artifacts, cleanup_events),
        validate_recommendations(cleanup_events, recommendations),
    ]
    overall = OK
    if any(c["status"] == FAIL for c in checks):
        overall = FAIL
    elif any(c["status"] == WARN for c in checks):
        overall = WARN
    return {"status": overall, "checks": checks}
