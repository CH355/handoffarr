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
