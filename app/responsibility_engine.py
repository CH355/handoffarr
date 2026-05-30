"""Responsibility attribution interpreter.

Pure rule helpers that turn persisted lifecycle evidence into canonical
ResponsibilityAssessment dictionaries. This module does not collect, persist, or
render anything; callers provide the already-observed facts.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from .cleanup import CLEANUP_FAILED, CLEANUP_PENDING
from .imports import IMPORT_FAILED, IMPORT_SUCCESS
from .library import LIBRARY_MISSING, LIBRARY_PRESENT

CONFIDENCE = {"Certain", "High", "Medium", "Low"}
DOMAINS = {
    "User",
    "Filesystem",
    "Network",
    "Indexer",
    "Seerr",
    "Radarr",
    "Sonarr",
    "Lidarr",
    "qBittorrent",
    "Cleanup Subsystem",
    "External Dependency",
    "Unknown",
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
    return f"responsibility:{digest}"


def _source_domain(value: Any) -> str:
    source = str(value or "").strip().lower()
    mapping = {"radarr": "Radarr", "sonarr": "Sonarr", "lidarr": "Lidarr"}
    return mapping.get(source, "Radarr")


def _assessment(
    *,
    assessment_id: str,
    lifecycle_stage: str,
    diagnosis: str,
    responsible_domain: str,
    confidence: str,
    evidence: dict[str, Any],
    impact: dict[str, Any],
    recommended_action: str,
    observed_at: str,
) -> dict[str, Any]:
    if confidence not in CONFIDENCE:
        confidence = "Low"
    if responsible_domain not in DOMAINS:
        responsible_domain = "Unknown"
    return {
        "assessment_id": assessment_id,
        "lifecycle_stage": lifecycle_stage,
        "diagnosis": diagnosis,
        "responsible_domain": responsible_domain,
        "confidence": confidence,
        "evidence": evidence,
        "impact": impact,
        "recommended_action": recommended_action,
        "observed_at": observed_at,
    }


def _trace_key(trace: dict[str, Any]) -> str:
    return str(
        trace.get("torrent_hash")
        or trace.get("download_id")
        or trace.get("radarr_history_id")
        or trace.get("title")
        or trace.get("id")
    )


def _cleanup_evidence(trace: dict[str, Any]) -> dict[str, Any]:
    return {
        "import_status": trace.get("import_status"),
        "library_status": trace.get("library_status"),
        "cleanup_status": trace.get("cleanup_status"),
        "torrent_state": trace.get("qbittorrent_state"),
        "torrent_hash": trace.get("torrent_hash"),
        "title": trace.get("title"),
        "messages": [
            "Import succeeded.",
            "Library exists.",
            f"{trace.get('cleanup_status')}.",
            "Torrent still exists." if trace.get("torrent_hash") else "Torrent evidence missing.",
        ],
    }


def _cleanup_impact(trace: dict[str, Any]) -> dict[str, Any]:
    retained_bytes = _to_int(trace.get("retained_bytes"))
    recoverable_bytes = _to_int(trace.get("recoverable_bytes"))
    return {
        "retained_bytes": retained_bytes,
        "recoverable_bytes": recoverable_bytes,
        "affected_items": 1,
    }


def _runtime_failure(trace: dict[str, Any]) -> bool:
    diagnosis = str(trace.get("diagnosis") or "").lower()
    state = str(trace.get("qbittorrent_state") or "").lower()
    runtime_terms = (
        "stalled",
        "stale indexer",
        "metadata",
        "tracker",
        "connectivity",
        "dead swarm",
        "choking",
        "vpn/network",
    )
    if any(term in diagnosis for term in runtime_terms):
        return True
    return state in {"stalleddl", "metadl"} or "tracker" in state


def build_responsibility_assessments(
    *,
    traces: list[dict[str, Any]],
    import_events: list[dict[str, Any]],
    library_artifacts: list[dict[str, Any]],
    cleanup_events: list[dict[str, Any]],
    storage_summary: dict[str, Any],
    observed_at: str | None = None,
) -> list[dict[str, Any]]:
    """Generate canonical responsibility assessments from derived evidence."""
    observed = observed_at or _utcnow()
    assessments: list[dict[str, Any]] = []
    emitted: set[tuple[str, str]] = set()

    for trace in traces:
        key = _trace_key(trace)
        import_status = trace.get("import_status")
        library_status = trace.get("library_status")
        cleanup_status = trace.get("cleanup_status")
        has_torrent = bool(trace.get("torrent_hash") or trace.get("qbittorrent_state"))

        if (
            import_status == IMPORT_SUCCESS
            and library_status == LIBRARY_PRESENT
            and has_torrent
            and cleanup_status == CLEANUP_PENDING
        ):
            emitted.add(("cleanup-pending", key))
            assessments.append(
                _assessment(
                    assessment_id=_stable_id("cleanup-pending", key),
                    lifecycle_stage="Cleanup",
                    diagnosis="Cleanup Pending",
                    responsible_domain="Cleanup Subsystem",
                    confidence="High",
                    evidence=_cleanup_evidence(trace),
                    impact=_cleanup_impact(trace),
                    recommended_action="Review cleanup policy.",
                    observed_at=observed,
                )
            )

        if (
            import_status == IMPORT_SUCCESS
            and library_status == LIBRARY_PRESENT
            and has_torrent
            and cleanup_status == CLEANUP_FAILED
        ):
            emitted.add(("cleanup-failed", key))
            assessments.append(
                _assessment(
                    assessment_id=_stable_id("cleanup-failed", key),
                    lifecycle_stage="Cleanup",
                    diagnosis="Cleanup Failure",
                    responsible_domain="Cleanup Subsystem",
                    confidence="High",
                    evidence=_cleanup_evidence(trace),
                    impact=_cleanup_impact(trace),
                    recommended_action="Review cleanup execution.",
                    observed_at=observed,
                )
            )

        if import_status == IMPORT_SUCCESS and library_status == LIBRARY_MISSING:
            emitted.add(("library-missing", key))
            assessments.append(
                _assessment(
                    assessment_id=_stable_id("library-missing", key),
                    lifecycle_stage="Library",
                    diagnosis="Library Integrity Failure",
                    responsible_domain="Filesystem",
                    confidence="Medium",
                    evidence={
                        "import_status": import_status,
                        "library_status": library_status,
                        "library_path": trace.get("library_path"),
                        "title": trace.get("title"),
                        "messages": [
                            "Import succeeded.",
                            "Expected library file is missing.",
                        ],
                    },
                    impact={"affected_items": 1},
                    recommended_action="Verify library path.",
                    observed_at=observed,
                )
            )

        if import_status == IMPORT_FAILED:
            domain = _source_domain(trace.get("imported_by"))
            emitted.add(("import-failed", key))
            assessments.append(
                _assessment(
                    assessment_id=_stable_id("import-failed", key),
                    lifecycle_stage="Import",
                    diagnosis="Import Failure",
                    responsible_domain=domain,
                    confidence="High",
                    evidence={
                        "import_status": import_status,
                        "source_application": trace.get("imported_by"),
                        "title": trace.get("title"),
                        "messages": ["Import failed."],
                    },
                    impact={"affected_items": 1},
                    recommended_action="Review import logs.",
                    observed_at=observed,
                )
            )

        if _runtime_failure(trace):
            emitted.add(("runtime-failed", key))
            assessments.append(
                _assessment(
                    assessment_id=_stable_id("runtime-failed", key),
                    lifecycle_stage="Runtime",
                    diagnosis="Runtime Failure",
                    responsible_domain="qBittorrent",
                    confidence="Medium",
                    evidence={
                        "diagnosis": trace.get("diagnosis"),
                        "torrent_state": trace.get("qbittorrent_state"),
                        "actual_seeds": trace.get("actual_seeds"),
                        "actual_peers": trace.get("actual_peers"),
                        "dlspeed": trace.get("dlspeed"),
                        "title": trace.get("title"),
                        "messages": ["Runtime evidence indicates stalled, metadata, or tracker failure."],
                    },
                    impact={"affected_items": 1},
                    recommended_action="Review runtime conditions.",
                    observed_at=observed,
                )
            )

    imports_by_media = {
        str(event.get("media_id") or event.get("import_id") or ""): event
        for event in import_events
    }
    for import_event in import_events:
        key = str(import_event.get("media_id") or import_event.get("import_id") or "")
        if not key or ("import-failed", key) in emitted:
            continue
        if import_event.get("import_status") != IMPORT_FAILED:
            continue
        domain = _source_domain(import_event.get("source_application"))
        emitted.add(("import-failed", key))
        assessments.append(
            _assessment(
                assessment_id=_stable_id("import-failed", key),
                lifecycle_stage="Import",
                diagnosis="Import Failure",
                responsible_domain=domain,
                confidence="High",
                evidence={
                    "import_status": import_event.get("import_status"),
                    "source_application": import_event.get("source_application"),
                    "media_title": import_event.get("media_title"),
                    "messages": ["Import failed."],
                },
                impact={"affected_items": 1},
                recommended_action="Review import logs.",
                observed_at=observed,
            )
        )

    for artifact in library_artifacts:
        key = str(artifact.get("media_id") or artifact.get("artifact_id") or "")
        if not key or ("library-missing", key) in emitted:
            continue
        import_event = imports_by_media.get(str(artifact.get("media_id") or ""))
        if not (
            import_event
            and import_event.get("import_status") == IMPORT_SUCCESS
            and artifact.get("library_status") == LIBRARY_MISSING
        ):
            continue
        emitted.add(("library-missing", key))
        assessments.append(
            _assessment(
                assessment_id=_stable_id("library-missing", key),
                lifecycle_stage="Library",
                diagnosis="Library Integrity Failure",
                responsible_domain="Filesystem",
                confidence="Medium",
                evidence={
                    "import_status": IMPORT_SUCCESS,
                    "library_status": artifact.get("library_status"),
                    "library_path": artifact.get("library_path"),
                    "media_title": artifact.get("media_title"),
                    "messages": [
                        "Import succeeded.",
                        "Expected library file is missing.",
                    ],
                },
                impact={"affected_items": 1},
                recommended_action="Verify library path.",
                observed_at=observed,
            )
        )

    for cleanup_event in cleanup_events:
        key = str(cleanup_event.get("torrent_hash") or cleanup_event.get("media_id") or cleanup_event.get("cleanup_id") or "")
        status = cleanup_event.get("cleanup_status")
        if not key or status not in {CLEANUP_PENDING, CLEANUP_FAILED}:
            continue
        rule = "cleanup-pending" if status == CLEANUP_PENDING else "cleanup-failed"
        if (rule, key) in emitted:
            continue
        diagnosis = "Cleanup Pending" if status == CLEANUP_PENDING else "Cleanup Failure"
        action = "Review cleanup policy." if status == CLEANUP_PENDING else "Review cleanup execution."
        emitted.add((rule, key))
        assessments.append(
            _assessment(
                assessment_id=_stable_id(rule, key),
                lifecycle_stage="Cleanup",
                diagnosis=diagnosis,
                responsible_domain="Cleanup Subsystem",
                confidence="High",
                evidence={
                    "cleanup_status": status,
                    "torrent_hash": cleanup_event.get("torrent_hash"),
                    "media_title": cleanup_event.get("media_title"),
                    "messages": [
                        "Cleanup event indicates retained download storage.",
                    ],
                },
                impact={
                    "retained_bytes": _to_int(cleanup_event.get("retained_bytes")),
                    "recoverable_bytes": _to_int(cleanup_event.get("recoverable_bytes")),
                    "affected_items": 1,
                },
                recommended_action=action,
                observed_at=observed,
            )
        )

    cleanup_pending = [
        event
        for event in cleanup_events
        if event.get("cleanup_status") in {CLEANUP_PENDING, CLEANUP_FAILED}
    ]
    recoverable_bytes = sum(_to_int(event.get("recoverable_bytes")) for event in cleanup_pending)
    retained_bytes = sum(_to_int(event.get("retained_bytes")) for event in cleanup_pending)
    affected_items = len(cleanup_pending)
    summary = storage_summary.get("summary") or {}
    storage_retained = _to_int(summary.get("retained_bytes"))
    completed_count = _to_int(summary.get("completed_torrent_count"))

    if affected_items and (recoverable_bytes > 0 or storage_retained > 0):
        assessments.append(
            _assessment(
                assessment_id=_stable_id("storage-failure", affected_items, recoverable_bytes, storage_retained),
                lifecycle_stage="Storage",
                diagnosis="Storage Failure",
                responsible_domain="Cleanup Subsystem",
                confidence="High",
                evidence={
                    "import_status": IMPORT_SUCCESS,
                    "library_status": LIBRARY_PRESENT,
                    "cleanup_status": "Cleanup Pending",
                    "storage_retained": True,
                    "messages": [
                        "Import succeeded.",
                        "Library exists.",
                        "Cleanup pending.",
                        "Storage retained.",
                    ],
                },
                impact={
                    "retained_bytes": retained_bytes or storage_retained,
                    "recoverable_bytes": recoverable_bytes,
                    "affected_items": affected_items,
                    "affected_torrents": completed_count or affected_items,
                },
                recommended_action="Review cleanup policy.",
                observed_at=observed,
            )
        )

    assessments.sort(key=_assessment_priority)
    return _dedupe(assessments)


def _assessment_priority(assessment: dict[str, Any]) -> tuple[int, int, str]:
    diagnosis_rank = {
        "Storage Failure": 0,
        "Cleanup Failure": 1,
        "Cleanup Pending": 2,
        "Import Failure": 3,
        "Library Integrity Failure": 4,
        "Runtime Failure": 5,
    }
    confidence_rank = {"Certain": 0, "High": 1, "Medium": 2, "Low": 3}
    impact = assessment.get("impact") or {}
    return (
        diagnosis_rank.get(str(assessment.get("diagnosis")), 99),
        confidence_rank.get(str(assessment.get("confidence")), 99),
        str(-_to_int(impact.get("recoverable_bytes") or impact.get("retained_bytes"))),
    )


def _dedupe(assessments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for assessment in assessments:
        assessment_id = str(assessment.get("assessment_id"))
        if assessment_id in seen:
            continue
        seen.add(assessment_id)
        unique.append(assessment)
    return unique


def summarize_assessments(assessments: list[dict[str, Any]]) -> dict[str, Any]:
    domains = Counter(str(a.get("responsible_domain") or "Unknown") for a in assessments)
    diagnoses = Counter(str(a.get("diagnosis") or "Unknown") for a in assessments)
    top = assessments[0] if assessments else None
    return {
        "top_diagnosis": top.get("diagnosis") if top else None,
        "top_responsible_domain": top.get("responsible_domain") if top else None,
        "assessment_count": len(assessments),
        "top_responsible_domains": [
            {"domain": domain, "count": count}
            for domain, count in domains.most_common()
        ],
        "diagnoses": [
            {"diagnosis": diagnosis, "count": count}
            for diagnosis, count in diagnoses.most_common()
        ],
    }
