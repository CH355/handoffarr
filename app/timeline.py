"""Lifecycle (timeline) projection over persisted handoff traces.

This module performs **no interpretation**. It is a pure presentation transform
that reshapes the already-computed interpreter outputs carried on a
``handoff_traces`` row -- ``diagnosis``, ``state_classification``,
``match_source``, ``match_confidence``, ``match_reasons`` -- into the canonical
lifecycle shape defined in docs/architecture/pipeline-model.md.

It never re-derives health, never applies a threshold, and never does I/O. Every
judgment shown originates from a field an interpreter already wrote
(``correlation.diagnose`` / ``states.classify``). The only logic here is mapping
those existing labels onto lifecycle stages and choosing presentation badges --
the dashboard/visualization layer's job per interpreter-model.md.

Richer live findings (per-torrent tracker/runtime reasons, fleet queue findings)
remain in the ephemeral interpreters and are fetched on demand by the template
via the existing ``/api/debug/*`` endpoints, not recomputed here.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

# Canonical lifecycle stages, in order, from pipeline-model.md. The intermediate
# "search" / "candidate discovery" / "import" phases are inferred, not observed,
# so the operator-facing timeline collapses to the seven stages we can show.
LIFECYCLE_STAGES = (
    "request",
    "decision",
    "handoff",
    "queueing",
    "runtime",
    "diagnosis",
    "outcome",
)

# Confidence at/above this is a strong join (torrent hash 1.0, download id 0.8);
# below it is the fuzzy normalized-title path (0.5) flagged as low confidence.
STRONG_CONFIDENCE = 0.8


def _degradation(diagnosis: str | None) -> dict[str, Any]:
    """Localize an *existing* diagnosis label onto the lifecycle stage where the
    handoff degraded. This is a lookup over interpreter output, not a new
    judgment -- the diagnosis string itself was decided in ``correlation.diagnose``.
    """
    d = diagnosis or ""
    if "Healthy" in d or "Completed" in d or "seeding" in d:
        return {"degraded": False, "stage": None, "label": None}
    if "Likely bad low-availability" in d:
        return {
            "degraded": True,
            "stage": "selection",
            "label": "degraded at selection",
        }
    if "stale indexer" in d:
        return {"degraded": True, "stage": "runtime", "label": "degraded at runtime"}
    if "queue, disk, or peer choking" in d:
        return {
            "degraded": True,
            "stage": "queueing",
            "label": "degraded at queueing",
        }
    if "VPN/network" in d:
        return {
            "degraded": True,
            "stage": "operational",
            "label": "degraded due to operational bottleneck",
        }
    if "did not receive or expose" in d:
        return {
            "degraded": True,
            "stage": "missing_telemetry",
            "label": "degraded due to missing telemetry",
        }
    if "not yet handed" in d or "correlation failed" in d:
        return {"degraded": True, "stage": "handoff", "label": "degraded at handoff"}
    # Unknown/forward-compatible diagnosis: surface as degraded but unlocalized
    # rather than silently dropping it.
    return {"degraded": True, "stage": None, "label": "degraded"}


def _status(trace: dict[str, Any], degraded: bool) -> str:
    """Primary status indicator (req: healthy/degraded/stalled/completed/queued).

    Derived only from the persisted ``diagnosis`` and ``state_classification``;
    'stalled' is the runtime sub-type of a degraded download, 'queued' the
    in-flight sub-type of a not-yet-degraded one.
    """
    cls = (trace.get("state_classification") or "").lower()
    diagnosis = trace.get("diagnosis") or ""
    if "Completed" in diagnosis or cls in ("completed", "uploading"):
        return "completed"
    if degraded:
        return "stalled" if cls == "stalled" else "degraded"
    if cls == "queued":
        return "queued"
    return "healthy"


def _stage_status(present: bool, *, degraded_here: bool, reached: bool) -> str:
    """Visual status for one lifecycle node: bad if degradation localized here,
    ok if the item passed through it, pending if not yet reached, na otherwise."""
    if degraded_here:
        return "bad"
    if present:
        return "ok"
    return "pending" if reached else "na"


def project_trace(trace: dict[str, Any]) -> dict[str, Any]:
    """Reshape one persisted trace into a lifecycle pipeline."""
    diagnosis = trace.get("diagnosis")
    degradation = _degradation(diagnosis)
    degraded = degradation["degraded"]
    stage = degradation["stage"]
    status = _status(trace, degraded)

    has_request = trace.get("seerr_request_id") is not None
    has_decision = trace.get("radarr_history_id") is not None
    has_match = trace.get("match_source") is not None
    has_runtime = trace.get("qbittorrent_state") is not None
    cls = (trace.get("state_classification") or "").lower()

    conf = trace.get("match_confidence")
    low_confidence = (
        has_match and conf is not None and conf < STRONG_CONFIDENCE
    )
    # Telemetry gaps once an item has actually reached a decision: the fragile
    # reported_seeds point (telemetry.md gap #2) or runtime never captured.
    missing_telemetry = has_decision and (
        trace.get("reported_seeds") is None or not has_runtime
    )

    flags = {
        "problematic": degraded,
        "low_confidence": low_confidence,
        "stalled": cls == "stalled",
        "queued": cls == "queued",
        "completed": status == "completed",
        "missing_telemetry": missing_telemetry,
    }

    stages = {
        "request": {
            "status": _stage_status(has_request, degraded_here=False, reached=True),
            "present": has_request,
            "request_id": trace.get("seerr_request_id"),
            "request_status": trace.get("seerr_status"),
            "title": trace.get("title"),
        },
        "decision": {
            "status": _stage_status(
                has_decision, degraded_here=stage == "selection", reached=True
            ),
            "present": has_decision,
            "radarr_history_id": trace.get("radarr_history_id"),
            "selected_release": trace.get("selected_release"),
            "reported_seeds": trace.get("reported_seeds"),
            "indexer": trace.get("reported_indexer"),
        },
        "handoff": {
            "status": _stage_status(
                has_match,
                degraded_here=stage in ("handoff", "missing_telemetry"),
                reached=has_decision,
            ),
            "present": has_match,
            "match_source": trace.get("match_source"),
            "match_confidence": conf,
            "low_confidence": low_confidence,
            "torrent_hash": trace.get("torrent_hash"),
            "download_id": trace.get("download_id"),
        },
        "queueing": {
            "status": _stage_status(
                cls == "queued" or has_runtime,
                degraded_here=stage == "queueing",
                reached=has_match,
            ),
            "present": has_runtime,
            "queued": cls == "queued",
            "qbittorrent_state": trace.get("qbittorrent_state"),
        },
        "runtime": {
            "status": _stage_status(
                has_runtime,
                degraded_here=stage in ("runtime", "operational"),
                reached=has_match,
            ),
            "present": has_runtime,
            "qbittorrent_state": trace.get("qbittorrent_state"),
            "state_classification": trace.get("state_classification"),
            "peers": trace.get("actual_peers"),
            "seeds": trace.get("actual_seeds"),
            "dlspeed": trace.get("dlspeed"),
        },
        "diagnosis": {
            "status": "bad" if degraded else "ok",
            "present": diagnosis is not None,
            "diagnosis": diagnosis,
            "degradation_stage": stage,
            "degradation_label": degradation["label"],
        },
        "outcome": {
            "status": {
                "completed": "ok",
                "healthy": "ok",
                "queued": "warn",
                "stalled": "bad",
                "degraded": "bad",
            }.get(status, "warn"),
            "label": status,
        },
    }

    return {
        "title": trace.get("title") or "—",
        "status": status,
        "flags": flags,
        "degradation": degradation,
        "stages": stages,
        "why": {
            # match reasons are persisted; tracker/queue/runtime findings are
            # ephemeral interpreter output fetched on demand via /api/debug/*.
            "match_reasons": trace.get("match_reasons") or [],
            "torrent_hash": trace.get("torrent_hash"),
        },
        "updated_at": trace.get("updated_at"),
    }


def build_timeline(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Project all traces into the lifecycle structure plus a summary card.

    Returns ``{"summary": {...}, "pipelines": [...]}``. The summary counters are
    plain tallies over the per-pipeline flags -- no interpretation.
    """
    pipelines = [project_trace(t) for t in traces]

    summary = {
        "total_requests": len(pipelines),
        "healthy": sum(1 for p in pipelines if p["status"] == "healthy"),
        "degraded": sum(1 for p in pipelines if p["flags"]["problematic"]),
        "stalled_runtime": sum(1 for p in pipelines if p["flags"]["stalled"]),
        "low_confidence": sum(1 for p in pipelines if p["flags"]["low_confidence"]),
        "missing_telemetry": sum(
            1 for p in pipelines if p["flags"]["missing_telemetry"]
        ),
    }

    return {"summary": summary, "pipelines": pipelines}


# --- TimelineEvent interpreter (Phase 6 — Lifecycle View) -----------------
#
# A *separate* projection from build_timeline() above: rather than reshaping
# one trace into pipeline stages, this rebuilds a discrete TimelineEvent log
# across every persisted lifecycle signal so a single media item can be
# tracked through Request -> Decision -> Queue -> Runtime -> Import -> Library
# -> Cleanup -> Responsibility -> Recommendation -> Outcome. Pure interpreter:
# no collectors, no live calls -- everything is read off persisted snapshots.

CANONICAL_STAGES = (
    "Request",
    "Decision",
    "Queue",
    "Runtime",
    "Import",
    "Library",
    "Cleanup",
    "Responsibility",
    "Recommendation",
    "Outcome",
)

STAGE_COMPLETE = "Complete"
STAGE_FAILED = "Failed"
STAGE_PENDING = "Pending"
STAGE_UNKNOWN = "Unknown"
STAGE_STATUSES = {STAGE_COMPLETE, STAGE_FAILED, STAGE_PENDING, STAGE_UNKNOWN}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_timeline_id(media_id: str) -> str:
    digest = hashlib.sha1(str(media_id).encode("utf-8")).hexdigest()[:12]
    return f"timeline:{digest}"


def _trace_media_id(trace: dict[str, Any]) -> str:
    """Best stable identifier for a trace's lifecycle.

    Prefers normalized title so the same item correlates with import / library
    / cleanup records (which key by normalized title or media_id). Falls back
    to torrent hash, radarr id, or seerr id so every trace gets *some* key.
    """
    for key in (
        "normalized_title",
        "torrent_hash",
        "radarr_history_id",
        "seerr_request_id",
        "title",
    ):
        value = trace.get(key)
        if value:
            return str(value).strip().lower()
    return f"trace:{trace.get('id') or trace.get('updated_at') or 'unknown'}"


def _runtime_status(trace: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    cls = (trace.get("state_classification") or "").lower()
    state = (trace.get("qbittorrent_state") or "").lower()
    diagnosis = trace.get("diagnosis") or ""
    evidence = {
        "qbittorrent_state": trace.get("qbittorrent_state"),
        "state_classification": trace.get("state_classification"),
        "diagnosis": diagnosis,
    }
    if cls in ("completed", "uploading") or "Completed" in diagnosis or "seeding" in diagnosis:
        return STAGE_COMPLETE, evidence
    runtime_failure_terms = (
        "stalled",
        "metadata",
        "tracker",
        "dead swarm",
        "choking",
        "VPN/network",
        "stale indexer",
    )
    if any(term.lower() in diagnosis.lower() for term in runtime_failure_terms):
        return STAGE_FAILED, evidence
    if cls in ("queued", "downloading") or state:
        return STAGE_PENDING, evidence
    return STAGE_UNKNOWN, evidence


def _queue_status(trace: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    cls = (trace.get("state_classification") or "").lower()
    state = trace.get("qbittorrent_state")
    evidence = {
        "qbittorrent_state": state,
        "state_classification": trace.get("state_classification"),
    }
    if state or cls:
        return STAGE_COMPLETE, evidence
    return STAGE_PENDING, evidence


def _import_status(trace: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    status = trace.get("import_status")
    evidence = {
        "import_status": status,
        "imported_by": trace.get("imported_by"),
        "import_timestamp": trace.get("import_timestamp"),
    }
    if status == "Import Success":
        return STAGE_COMPLETE, evidence
    if status == "Import Failed":
        return STAGE_FAILED, evidence
    if status == "Import Pending":
        return STAGE_PENDING, evidence
    return STAGE_UNKNOWN, {"message": "No import event observed."}


def _library_status(trace: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    status = trace.get("library_status")
    evidence = {
        "library_status": status,
        "library_path": trace.get("library_path"),
        "library_size": trace.get("library_size"),
    }
    if status == "Library Present":
        return STAGE_COMPLETE, evidence
    if status == "Library Missing":
        return STAGE_FAILED, evidence
    if status == "Library Unknown":
        return STAGE_UNKNOWN, evidence
    return STAGE_UNKNOWN, {"message": "No library artifact observed."}


def _cleanup_status(trace: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    status = trace.get("cleanup_status")
    evidence = {
        "cleanup_status": status,
        "retained_bytes": trace.get("retained_bytes"),
        "recoverable_bytes": trace.get("recoverable_bytes"),
    }
    if status == "Cleanup Completed":
        return STAGE_COMPLETE, evidence
    if status == "Cleanup Pending":
        return STAGE_PENDING, evidence
    if status == "Cleanup Failed":
        return STAGE_FAILED, evidence
    return STAGE_UNKNOWN, {"message": "No cleanup event observed."}


def _request_status(trace: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    seerr_id = trace.get("seerr_request_id")
    if seerr_id:
        return STAGE_COMPLETE, {
            "seerr_request_id": seerr_id,
            "seerr_status": trace.get("seerr_status"),
        }
    if trace.get("radarr_history_id") or trace.get("torrent_hash"):
        return STAGE_COMPLETE, {"message": "Lifecycle entry observed without Seerr id."}
    return STAGE_PENDING, {"message": "No request observed."}


def _decision_status(trace: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    has_decision = trace.get("radarr_history_id") is not None
    has_match = trace.get("match_source") is not None
    evidence = {
        "radarr_history_id": trace.get("radarr_history_id"),
        "match_source": trace.get("match_source"),
        "match_confidence": trace.get("match_confidence"),
        "selected_release": trace.get("selected_release"),
    }
    if has_decision and has_match:
        return STAGE_COMPLETE, evidence
    if has_decision:
        return STAGE_PENDING, evidence
    return STAGE_PENDING, {"message": "Awaiting Radarr decision."}


def _responsibility_for_trace(
    assessments: list[dict[str, Any]],
    *,
    lifecycle_has_problem: bool,
) -> tuple[str, dict[str, Any]]:
    if not assessments:
        if lifecycle_has_problem:
            return STAGE_PENDING, {"message": "Lifecycle blocked; no responsibility assessment yet."}
        return STAGE_COMPLETE, {"message": "Lifecycle healthy; no assessment required."}
    top = assessments[0]
    return STAGE_COMPLETE, {
        "assessment_id": top.get("assessment_id"),
        "responsible_domain": top.get("responsible_domain"),
        "diagnosis": top.get("diagnosis"),
        "confidence": top.get("confidence"),
        "count": len(assessments),
    }


def _recommendation_for_trace(
    recommendations: list[dict[str, Any]],
    *,
    lifecycle_has_problem: bool,
) -> tuple[str, dict[str, Any]]:
    if not recommendations:
        if lifecycle_has_problem:
            return STAGE_PENDING, {"message": "Lifecycle blocked; no recommendation yet."}
        return STAGE_COMPLETE, {"message": "Lifecycle healthy; no recommendation required."}
    top = recommendations[0]
    return STAGE_COMPLETE, {
        "recommendation_id": top.get("recommendation_id"),
        "title": top.get("title"),
        "priority": top.get("priority"),
        "count": len(recommendations),
    }


def _outcome_for_stages(stages: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    # All stages except Outcome itself must be Complete for the lifecycle to
    # have landed successfully; any Failed or Pending blocks the outcome.
    blocking = [
        s for s in stages
        if s["stage"] != "Outcome" and s["stage_status"] in (STAGE_FAILED, STAGE_PENDING)
    ]
    if not blocking:
        return STAGE_COMPLETE, {"message": "Lifecycle completed successfully."}
    first = blocking[0]
    return STAGE_PENDING, {
        "blocked_at": first["stage"],
        "blocked_status": first["stage_status"],
        "message": f"Lifecycle blocked at {first['stage']}.",
    }


def build_timeline_events(
    *,
    traces: list[dict[str, Any]],
    responsibility_assessments: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    observed_at: str | None = None,
) -> list[dict[str, Any]]:
    """Synthesize TimelineEvent records from persisted lifecycle evidence.

    One TimelineEvent per (media, canonical stage). The stage_status field
    uses only canonical values (Complete / Failed / Pending / Unknown). Source
    points back to the interpreter that produced the underlying evidence.

    Trace rows already carry import / library / cleanup status thanks to
    ``correlation.build_traces``; we read those fields directly rather than
    re-correlating per stage here.
    """
    now = observed_at or _utcnow()

    events: list[dict[str, Any]] = []

    for trace in traces:
        media_id = _trace_media_id(trace)
        timeline_id = _stable_timeline_id(media_id)
        media_title = trace.get("title") or media_id
        updated_at = trace.get("updated_at") or now

        stages: list[dict[str, Any]] = []

        def _add(stage: str, status: str, source: str, evidence: dict[str, Any], ts: str | None = None) -> None:
            stages.append(
                {
                    "timeline_id": timeline_id,
                    "media_id": media_id,
                    "media_title": media_title,
                    "stage": stage,
                    "stage_status": status if status in STAGE_STATUSES else STAGE_UNKNOWN,
                    "source": source,
                    "timestamp": ts or updated_at,
                    "evidence": evidence,
                }
            )

        status, evidence = _request_status(trace)
        _add("Request", status, "correlation", evidence)

        status, evidence = _decision_status(trace)
        _add("Decision", status, "correlation", evidence)

        status, evidence = _queue_status(trace)
        _add("Queue", status, "correlation", evidence)

        status, evidence = _runtime_status(trace)
        _add("Runtime", status, "correlation", evidence)

        status, evidence = _import_status(trace)
        _add("Import", status, "imports", evidence, ts=trace.get("import_timestamp") or updated_at)

        status, evidence = _library_status(trace)
        _add("Library", status, "library", evidence)

        status, evidence = _cleanup_status(trace)
        _add("Cleanup", status, "cleanup", evidence)

        lifecycle_has_problem = any(
            s["stage_status"] in (STAGE_FAILED, STAGE_PENDING) for s in stages
        )

        status, evidence = _responsibility_for_trace(
            responsibility_assessments, lifecycle_has_problem=lifecycle_has_problem
        )
        _add("Responsibility", status, "responsibility", evidence)

        status, evidence = _recommendation_for_trace(
            recommendations, lifecycle_has_problem=lifecycle_has_problem
        )
        _add("Recommendation", status, "recommendations", evidence)

        status, evidence = _outcome_for_stages(stages)
        _add("Outcome", status, "timeline", evidence)

        events.extend(stages)

    return events


def _group_timeline_events(
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Group flat TimelineEvent rows into per-media lifecycle records."""
    by_timeline: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for event in events:
        timeline_id = event.get("timeline_id") or ""
        if timeline_id not in by_timeline:
            order.append(timeline_id)
            by_timeline[timeline_id] = {
                "timeline_id": timeline_id,
                "media_id": event.get("media_id"),
                "media_title": event.get("media_title"),
                "stages": [],
                "blocked_at": None,
                "responsible_domain": None,
                "recommendation": None,
                "outcome": None,
                "latest_timestamp": event.get("timestamp"),
            }
        record = by_timeline[timeline_id]
        record["stages"].append(
            {
                "stage": event.get("stage"),
                "stage_status": event.get("stage_status"),
                "source": event.get("source"),
                "timestamp": event.get("timestamp"),
                "evidence": event.get("evidence") or {},
            }
        )
        ts = event.get("timestamp") or ""
        if ts and ts > (record["latest_timestamp"] or ""):
            record["latest_timestamp"] = ts

    for record in by_timeline.values():
        # Order stages canonically so the UI always reads left-to-right.
        rank = {name: idx for idx, name in enumerate(CANONICAL_STAGES)}
        record["stages"].sort(key=lambda s: rank.get(s.get("stage") or "", 99))
        blocking = next(
            (
                s for s in record["stages"]
                if s["stage"] != "Outcome"
                and s["stage_status"] in (STAGE_FAILED, STAGE_PENDING)
            ),
            None,
        )
        if blocking:
            record["blocked_at"] = blocking["stage"]
        for stage in record["stages"]:
            if stage["stage"] == "Responsibility":
                record["responsible_domain"] = (stage["evidence"] or {}).get(
                    "responsible_domain"
                )
            elif stage["stage"] == "Recommendation":
                record["recommendation"] = (stage["evidence"] or {}).get("title")
            elif stage["stage"] == "Outcome":
                record["outcome"] = stage["stage_status"]
    return [by_timeline[tid] for tid in order]


def summarize_timeline_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    timelines = _group_timeline_events(events)
    completed = sum(1 for t in timelines if t.get("outcome") == STAGE_COMPLETE)
    blocked = sum(1 for t in timelines if t.get("blocked_at"))
    failed_stage_counts: dict[str, int] = {}
    for timeline in timelines:
        for stage in timeline["stages"]:
            if stage["stage_status"] == STAGE_FAILED:
                key = stage["stage"]
                failed_stage_counts[key] = failed_stage_counts.get(key, 0) + 1
    return {
        "total_timelines": len(timelines),
        "completed": completed,
        "blocked": blocked,
        "failed_by_stage": failed_stage_counts,
    }


def timeline_response(events: list[dict[str, Any]]) -> dict[str, Any]:
    timelines = _group_timeline_events(events)
    recent = sorted(
        timelines,
        key=lambda t: t.get("latest_timestamp") or "",
        reverse=True,
    )
    return {
        "summary": summarize_timeline_events(events),
        "recent_timelines": recent[:20],
    }


def media_timeline_response(media_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    matching = [e for e in events if str(e.get("media_id")) == str(media_id)]
    grouped = _group_timeline_events(matching)
    timeline = grouped[0] if grouped else None
    return {
        "media_id": media_id,
        "timeline": timeline,
        "stages": timeline["stages"] if timeline else [],
        "blocked_at": timeline.get("blocked_at") if timeline else None,
        "outcome": timeline.get("outcome") if timeline else None,
    }


def run_timeline() -> int:
    """Rebuild and persist the current TimelineEvent snapshot."""
    from . import db

    events = build_timeline_events(
        traces=db.all_traces(),
        responsibility_assessments=db.all_responsibility_assessments(),
        recommendations=db.all_recommendations(),
    )
    db.replace_timeline_events(events)
    return len(events)
