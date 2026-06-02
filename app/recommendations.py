"""Recommendations interpreter.

Pure rule helpers that turn persisted lifecycle evidence and derived
ResponsibilityAssessments into canonical Recommendation dictionaries. This
module does not collect, persist, or render anything; callers provide the
already-observed facts.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from .cleanup import CLEANUP_FAILED, CLEANUP_PENDING
from .imports import IMPORT_FAILED, IMPORT_PENDING, IMPORT_SUCCESS
from .library import LIBRARY_MISSING, LIBRARY_PRESENT

PRIORITIES = ("Critical", "High", "Medium", "Low")
PRIORITY_RANK = {p: i for i, p in enumerate(PRIORITIES)}

CATEGORIES = {
    "Storage Recovery",
    "Cleanup Policy",
    "Import Review",
    "Library Integrity",
    "Runtime Health",
    "Queue Optimization",
    "Network Review",
    "Configuration Review",
}

CONFIDENCES = {"Certain", "High", "Medium", "Low"}

# Thresholds used to decide priority. Bytes thresholds are conservative; they
# mirror the storage-thresholds default surface so a "large" recoverable total
# only becomes Critical once it crosses the configured retained-bytes ceiling.
DEFAULT_THRESHOLDS = {
    "storage_recovery_critical_bytes": 107374182400,  # 100 GiB
    "storage_recovery_high_bytes": 10737418240,        # 10 GiB
    "cleanup_policy_min_items": 5,
    "import_pending_min": 5,
    "runtime_failure_min": 1,
    "queue_saturation_min": 5,
    "network_failure_min": 1,
}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _stable_id(*parts: Any) -> str:
    raw = ":".join(str(part or "") for part in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"recommendation:{digest}"


def _recommendation(
    *,
    recommendation_id: str,
    priority: str,
    category: str,
    title: str,
    summary: str,
    recommended_action: str,
    expected_impact: dict[str, Any],
    confidence: str,
    evidence: dict[str, Any],
    related_assessment_id: str | None,
    observed_at: str,
) -> dict[str, Any]:
    if priority not in PRIORITY_RANK:
        priority = "Low"
    if category not in CATEGORIES:
        category = "Configuration Review"
    if confidence not in CONFIDENCES:
        confidence = "Low"
    return {
        "recommendation_id": recommendation_id,
        "priority": priority,
        "category": category,
        "title": title,
        "summary": summary,
        "recommended_action": recommended_action,
        "expected_impact": expected_impact,
        "confidence": confidence,
        "evidence": evidence,
        "related_assessment_id": related_assessment_id,
        "observed_at": observed_at,
    }


def _find_assessment(
    assessments: list[dict[str, Any]], diagnosis: str
) -> dict[str, Any] | None:
    for assessment in assessments:
        if str(assessment.get("diagnosis")) == diagnosis:
            return assessment
    return None


def _runtime_terms(value: Any) -> bool:
    text = str(value or "").lower()
    return any(
        term in text
        for term in ("stalled", "metadata", "tracker", "dead swarm", "choking")
    )


def _network_terms(value: Any) -> bool:
    text = str(value or "").lower()
    return any(
        term in text
        for term in ("vpn", "network", "dht", "connectivity", "disconnected")
    )


def _queue_terms(value: Any) -> bool:
    text = str(value or "").lower()
    return any(
        term in text
        for term in ("queue saturated", "slots exhausted", "queue saturation", "slot exhaustion")
    )


def build_queue_summary(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive a lightweight queue summary from persisted traces.

    No live qBittorrent calls: this is read off whatever trace runtime state
    already exists, so the recommendations engine can stay I/O free.
    """
    stalled = metadata = queued = active = network = 0
    for trace in traces:
        state = str(trace.get("qbittorrent_state") or "").lower()
        diagnosis = str(trace.get("diagnosis") or "").lower()
        if state == "stalleddl" or "stalled" in diagnosis:
            stalled += 1
        if state == "metadl" or "metadata" in diagnosis:
            metadata += 1
        if state == "queueddl":
            queued += 1
        if state == "downloading":
            active += 1
        if _network_terms(diagnosis):
            network += 1
    return {
        "stalled_downloads": stalled,
        "metadata_downloads": metadata,
        "queued_downloads": queued,
        "active_downloads": active,
        "network_signal_count": network,
    }


def build_recommendations(
    *,
    assessments: list[dict[str, Any]],
    import_events: list[dict[str, Any]],
    library_artifacts: list[dict[str, Any]],
    cleanup_events: list[dict[str, Any]],
    storage_summary: dict[str, Any],
    queue_summary: dict[str, Any],
    traces: list[dict[str, Any]],
    thresholds: dict[str, int] | None = None,
    observed_at: str | None = None,
) -> list[dict[str, Any]]:
    """Generate Recommendation records from already-derived evidence."""
    cfg = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        cfg.update({k: int(v) for k, v in thresholds.items() if v is not None})
    observed = observed_at or _utcnow()
    out: list[dict[str, Any]] = []

    storage_assessment = _find_assessment(assessments, "Storage Failure")
    cleanup_pending = [
        e for e in cleanup_events if e.get("cleanup_status") == CLEANUP_PENDING
    ]
    cleanup_failed = [
        e for e in cleanup_events if e.get("cleanup_status") == CLEANUP_FAILED
    ]
    cleanup_actionable = cleanup_pending + cleanup_failed
    recoverable_bytes = sum(_to_int(e.get("recoverable_bytes")) for e in cleanup_actionable)
    retained_bytes = sum(_to_int(e.get("retained_bytes")) for e in cleanup_actionable)
    storage_section = storage_summary.get("summary") or {}
    storage_retained = _to_int(storage_section.get("retained_bytes"))
    storage_completed = _to_int(storage_section.get("completed_torrent_count"))
    storage_health = storage_section.get("health")

    # Rule 1 — Storage Recovery
    storage_evidence_present = bool(storage_assessment) or storage_health in {"critical", "warning"}
    impact_bytes = recoverable_bytes or storage_retained
    affected_items = len(cleanup_actionable) or storage_completed
    if storage_evidence_present and impact_bytes > 0:
        if impact_bytes >= cfg["storage_recovery_critical_bytes"]:
            priority = "Critical"
        elif impact_bytes >= cfg["storage_recovery_high_bytes"]:
            priority = "High"
        else:
            priority = "Medium"
        confidence = "High" if storage_assessment else "Medium"
        related_id = (
            storage_assessment.get("assessment_id") if storage_assessment else None
        )
        evidence = {
            "storage_health": storage_health,
            "storage_retained_bytes": storage_retained,
            "recoverable_bytes": recoverable_bytes,
            "affected_cleanup_items": len(cleanup_actionable),
            "completed_torrent_count": storage_completed,
            "messages": [
                "Storage pressure observed."
                if storage_health in {"critical", "warning"}
                else "Storage failure diagnosed.",
                f"{len(cleanup_actionable)} cleanup candidate(s) actionable.",
            ],
        }
        out.append(
            _recommendation(
                recommendation_id=_stable_id("storage-recovery", impact_bytes, affected_items),
                priority=priority,
                category="Storage Recovery",
                title="Review cleanup candidates to recover storage",
                summary=(
                    f"{affected_items} retained item(s) account for "
                    f"{impact_bytes} bytes of recoverable storage."
                ),
                recommended_action=(
                    "Review top cleanup candidates and remove only after "
                    "confirming library copies."
                ),
                expected_impact={
                    "recoverable_bytes": impact_bytes,
                    "affected_items": affected_items,
                },
                confidence=confidence,
                evidence=evidence,
                related_assessment_id=related_id,
                observed_at=observed,
            )
        )

    # Rule 2 — Cleanup Policy
    confirmed_retained = []
    artifacts_by_media = {
        str(a.get("media_id")): a for a in library_artifacts if a.get("media_id")
    }
    imports_by_media = {
        str(i.get("media_id")): i for i in import_events if i.get("media_id")
    }
    for event in cleanup_pending:
        media_id = str(event.get("media_id") or "")
        import_event = imports_by_media.get(media_id)
        artifact = artifacts_by_media.get(media_id)
        evidence = event.get("evidence") or {}
        import_ok = (
            (import_event and import_event.get("import_status") == IMPORT_SUCCESS)
            or evidence.get("import_status") == IMPORT_SUCCESS
        )
        library_ok = (
            (artifact and artifact.get("file_exists"))
            or evidence.get("library_status") == LIBRARY_PRESENT
        )
        torrent_present = bool(event.get("torrent_hash")) or bool(
            evidence.get("torrent_present")
        )
        if import_ok and library_ok and torrent_present:
            confirmed_retained.append(event)
    if len(confirmed_retained) >= cfg["cleanup_policy_min_items"]:
        cleanup_assessment = _find_assessment(assessments, "Cleanup Pending") or _find_assessment(
            assessments, "Cleanup Failure"
        )
        impact_items = len(confirmed_retained)
        impact_bytes = sum(_to_int(e.get("retained_bytes")) for e in confirmed_retained)
        priority = "High" if impact_items >= cfg["cleanup_policy_min_items"] * 2 else "Medium"
        out.append(
            _recommendation(
                recommendation_id=_stable_id("cleanup-policy", impact_items, impact_bytes),
                priority=priority,
                category="Cleanup Policy",
                title="Review remove-imported-downloads policy",
                summary=(
                    f"{impact_items} imported item(s) retained their downloads "
                    "after successful import and library presence."
                ),
                recommended_action=(
                    "Check Sonarr/Radarr/Lidarr download client cleanup settings."
                ),
                expected_impact={
                    "retained_bytes": impact_bytes,
                    "affected_items": impact_items,
                },
                confidence="High",
                evidence={
                    "confirmed_retained_count": impact_items,
                    "sample_titles": [
                        e.get("media_title") for e in confirmed_retained[:5] if e.get("media_title")
                    ],
                    "messages": [
                        "Imports succeeded.",
                        "Library files present.",
                        "Torrents retained.",
                    ],
                },
                related_assessment_id=(
                    cleanup_assessment.get("assessment_id") if cleanup_assessment else None
                ),
                observed_at=observed,
            )
        )

    # Rule 3 — Library Integrity
    library_missing: list[dict[str, Any]] = []
    for artifact in library_artifacts:
        media_id = str(artifact.get("media_id") or "")
        import_event = imports_by_media.get(media_id)
        if (
            import_event
            and import_event.get("import_status") == IMPORT_SUCCESS
            and artifact.get("library_status") == LIBRARY_MISSING
        ):
            library_missing.append(artifact)
    if library_missing:
        library_assessment = _find_assessment(assessments, "Library Integrity Failure")
        priority = "High" if len(library_missing) >= 5 else "Medium"
        out.append(
            _recommendation(
                recommendation_id=_stable_id("library-integrity", len(library_missing)),
                priority=priority,
                category="Library Integrity",
                title="Verify missing library files",
                summary=(
                    f"{len(library_missing)} imported item(s) report library "
                    "files as missing."
                ),
                recommended_action=(
                    "Check library path, mount, permissions, and import destination."
                ),
                expected_impact={"affected_items": len(library_missing)},
                confidence="Medium",
                evidence={
                    "missing_paths": [
                        a.get("library_path") for a in library_missing[:5] if a.get("library_path")
                    ],
                    "messages": [
                        "Imports succeeded.",
                        "Expected library files are absent on disk.",
                    ],
                },
                related_assessment_id=(
                    library_assessment.get("assessment_id") if library_assessment else None
                ),
                observed_at=observed,
            )
        )

    # Rule 4 — Import Review
    import_failed = [e for e in import_events if e.get("import_status") == IMPORT_FAILED]
    import_pending = [e for e in import_events if e.get("import_status") == IMPORT_PENDING]
    if import_failed or len(import_pending) >= cfg["import_pending_min"]:
        import_assessment = _find_assessment(assessments, "Import Failure")
        if import_failed and len(import_failed) >= 5:
            priority = "High"
        elif import_failed:
            priority = "Medium"
        else:
            priority = "Low"
        sources = sorted(
            {str(e.get("source_application") or "Unknown") for e in import_failed + import_pending}
        )
        out.append(
            _recommendation(
                recommendation_id=_stable_id(
                    "import-review", len(import_failed), len(import_pending)
                ),
                priority=priority,
                category="Import Review",
                title="Review failed or pending imports",
                summary=(
                    f"{len(import_failed)} failed import(s) and "
                    f"{len(import_pending)} pending import(s) observed."
                ),
                recommended_action=(
                    "Inspect application import logs and root folder mappings."
                ),
                expected_impact={
                    "affected_items": len(import_failed) + len(import_pending),
                    "failed": len(import_failed),
                    "pending": len(import_pending),
                },
                confidence="High" if import_failed else "Medium",
                evidence={
                    "source_applications": sources,
                    "messages": [
                        f"{len(import_failed)} import failure(s) observed.",
                        f"{len(import_pending)} import(s) pending classification.",
                    ],
                },
                related_assessment_id=(
                    import_assessment.get("assessment_id") if import_assessment else None
                ),
                observed_at=observed,
            )
        )

    # Rule 5 — Runtime Health
    runtime_traces = [
        t
        for t in traces
        if _runtime_terms(t.get("diagnosis")) or _runtime_terms(t.get("qbittorrent_state"))
    ]
    if len(runtime_traces) >= cfg["runtime_failure_min"]:
        runtime_assessment = _find_assessment(assessments, "Runtime Failure")
        priority = "High" if len(runtime_traces) >= 5 else "Medium"
        out.append(
            _recommendation(
                recommendation_id=_stable_id("runtime-health", len(runtime_traces)),
                priority=priority,
                category="Runtime Health",
                title="Review stalled download health",
                summary=(
                    f"{len(runtime_traces)} download(s) show stalled, metadata, "
                    "or tracker failure signals."
                ),
                recommended_action=(
                    "Inspect stalled torrents, tracker status, and metadata "
                    "acquisition."
                ),
                expected_impact={"affected_items": len(runtime_traces)},
                confidence="Medium",
                evidence={
                    "sample_titles": [
                        t.get("title") for t in runtime_traces[:5] if t.get("title")
                    ],
                    "messages": [
                        "Runtime signals indicate stall, metadata, or tracker failure.",
                    ],
                },
                related_assessment_id=(
                    runtime_assessment.get("assessment_id") if runtime_assessment else None
                ),
                observed_at=observed,
            )
        )

    # Rule 6 — Queue Optimization
    queue_stalled = _to_int(queue_summary.get("stalled_downloads"))
    queue_queued = _to_int(queue_summary.get("queued_downloads"))
    queue_active = _to_int(queue_summary.get("active_downloads"))
    queue_pressure = queue_queued >= cfg["queue_saturation_min"] or (
        queue_active > 0
        and queue_stalled >= max(2, queue_active)
    )
    if queue_pressure:
        priority = "Medium"
        out.append(
            _recommendation(
                recommendation_id=_stable_id(
                    "queue-optimization", queue_queued, queue_stalled, queue_active
                ),
                priority=priority,
                category="Queue Optimization",
                title="Review qBittorrent queue settings",
                summary=(
                    f"{queue_queued} queued and {queue_stalled} stalled "
                    "download(s) with limited active slots."
                ),
                recommended_action=(
                    "Increase active download limits or reduce backlog."
                ),
                expected_impact={
                    "queued_downloads": queue_queued,
                    "stalled_downloads": queue_stalled,
                    "active_downloads": queue_active,
                },
                confidence="Medium",
                evidence={
                    "queue_summary": queue_summary,
                    "messages": [
                        "Queue depth or stalled-to-active ratio indicates saturation.",
                    ],
                },
                related_assessment_id=None,
                observed_at=observed,
            )
        )

    # Rule 7 — Network Review
    network_traces = [
        t for t in traces if _network_terms(t.get("diagnosis"))
    ]
    network_signal = _to_int(queue_summary.get("network_signal_count"))
    if len(network_traces) >= cfg["network_failure_min"] or network_signal >= cfg["network_failure_min"]:
        priority = "High" if (len(network_traces) + network_signal) >= 3 else "Medium"
        out.append(
            _recommendation(
                recommendation_id=_stable_id("network-review", len(network_traces), network_signal),
                priority=priority,
                category="Network Review",
                title="Review network or VPN connectivity",
                summary=(
                    f"{len(network_traces)} download(s) flag VPN, DHT, or tracker "
                    "connectivity issues."
                ),
                recommended_action=(
                    "Check VPN, DNS, DHT, and tracker reachability."
                ),
                expected_impact={"affected_items": len(network_traces) or network_signal},
                confidence="Medium",
                evidence={
                    "sample_diagnoses": [
                        t.get("diagnosis") for t in network_traces[:5] if t.get("diagnosis")
                    ],
                    "messages": [
                        "Network signals indicate VPN, DHT, or tracker failure.",
                    ],
                },
                related_assessment_id=None,
                observed_at=observed,
            )
        )

    out.sort(key=_recommendation_sort_key)
    return _dedupe(out)


def _recommendation_sort_key(rec: dict[str, Any]) -> tuple[int, int, str]:
    impact = rec.get("expected_impact") or {}
    impact_bytes = -(
        _to_int(impact.get("recoverable_bytes"))
        or _to_int(impact.get("retained_bytes"))
    )
    return (
        PRIORITY_RANK.get(str(rec.get("priority")), 99),
        impact_bytes,
        str(rec.get("recommendation_id") or ""),
    )


def _dedupe(recs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for rec in recs:
        rid = str(rec.get("recommendation_id"))
        if rid in seen:
            continue
        seen.add(rid)
        unique.append(rec)
    return unique


def summarize_recommendations(recommendations: list[dict[str, Any]]) -> dict[str, Any]:
    counts_by_priority = {p: 0 for p in PRIORITIES}
    counts_by_category: dict[str, int] = {}
    total_recoverable_bytes = 0
    total_affected = 0
    for rec in recommendations:
        priority = str(rec.get("priority"))
        if priority in counts_by_priority:
            counts_by_priority[priority] += 1
        category = str(rec.get("category") or "Unknown")
        counts_by_category[category] = counts_by_category.get(category, 0) + 1
        impact = rec.get("expected_impact") or {}
        total_recoverable_bytes += _to_int(impact.get("recoverable_bytes"))
        total_affected += _to_int(impact.get("affected_items"))
    top = recommendations[0] if recommendations else None
    return {
        "total": len(recommendations),
        "counts_by_priority": counts_by_priority,
        "counts_by_category": counts_by_category,
        "total_recoverable_bytes": total_recoverable_bytes,
        "total_affected_items": total_affected,
        "top_priority": top.get("priority") if top else None,
        "top_category": top.get("category") if top else None,
        "top_title": top.get("title") if top else None,
    }


def top_cleanup_candidates(
    cleanup_events: list[dict[str, Any]], limit: int = 10
) -> list[dict[str, Any]]:
    actionable = [
        e
        for e in cleanup_events
        if e.get("cleanup_status") in {CLEANUP_PENDING, CLEANUP_FAILED}
    ]
    actionable.sort(key=lambda e: _to_int(e.get("retained_bytes")), reverse=True)
    out: list[dict[str, Any]] = []
    for event in actionable[:limit]:
        out.append(
            {
                "title": event.get("media_title") or event.get("torrent_hash"),
                "retained_bytes": _to_int(event.get("retained_bytes")),
                "cleanup_status": event.get("cleanup_status"),
                "confidence": "High" if event.get("cleanup_status") == CLEANUP_FAILED else "Medium",
                "media_id": event.get("media_id"),
            }
        )
    return out


def run_recommendations(config) -> int:
    """Build and persist the current recommendations snapshot.

    Imported lazily inside the function so the pure rule helpers above can be
    unit-tested without pulling in db / config side effects.
    """
    from . import db
    from .cleanup_reconciliation import (
        latest_completed_execution_index,
        matching_completed_execution,
    )
    from .responsibility import build_storage_summary

    traces = db.all_traces()
    completed_execution_index = latest_completed_execution_index(
        db.all_cleanup_executions(limit=5000)
    )
    cleanup_events = [
        event
        for event in db.all_cleanup_events()
        if not matching_completed_execution(event, completed_execution_index)
    ]
    recommendations = build_recommendations(
        assessments=db.all_responsibility_assessments(),
        import_events=db.all_import_events(),
        library_artifacts=db.all_library_artifacts(),
        cleanup_events=cleanup_events,
        storage_summary=build_storage_summary(config),
        queue_summary=build_queue_summary(traces),
        traces=traces,
    )
    db.replace_recommendations(recommendations)
    return len(recommendations)
