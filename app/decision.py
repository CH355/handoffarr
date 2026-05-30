"""Decision visibility interpreter.

Pure interpreter over persisted DecisionObservation rows (raw_events with
source=decision) plus the existing lifecycle facts (traces, imports, library,
cleanup). Produces ``DecisionAssessment`` records the dashboard can render to
answer:

- Why was this torrent selected?
- Which indexer supplied it?
- What alternatives existed?
- Was the selection reasonable?
- Did availability claims match reality?
- Who passed the bad torrent?

No collectors, no external I/O. Reads from ``db`` only.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from typing import Any

from . import db, states
from .config import Config

logger = logging.getLogger("handoffarr.decision")

# Canonical decision-quality vocabulary. Mirrors phase 8 requirements.
GOOD = "Good Selection"
ACCEPTABLE = "Acceptable Selection"
QUESTIONABLE = "Questionable Selection"
BAD = "Bad Selection"
UNKNOWN = "Unknown"
QUALITIES = {GOOD, ACCEPTABLE, QUESTIONABLE, BAD, UNKNOWN}

# Confidence vocabulary matches the responsibility model so the dashboard can
# reuse the existing wording ("Responsibility confirmed" / "Very likely
# responsible" / ...).
CERTAIN = "Certain"
HIGH = "High"
MEDIUM = "Medium"
LOW = "Low"

# Reported-seed thresholds used to detect availability misrepresentation. These
# fall back to the same defaults the correlation interpreter uses for diagnosis.
DEFAULT_LOW_REPORTED_SEEDS = 5
DEFAULT_HEALTHY_REPORTED_SEEDS = 20


def _parse_payload(event: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(event.get("payload_json") or "{}")
    except Exception:  # noqa: BLE001
        return {}


def _latest_observations() -> list[dict[str, Any]]:
    events = [
        event
        for event in db.recent_events(source="decision", limit=2000)
        if event.get("event_type") == "observation"
    ]
    seen: set[str] = set()
    observations: list[dict[str, Any]] = []
    for event in events:
        key = str(event.get("external_id") or event.get("id"))
        if key in seen:
            continue
        seen.add(key)
        payload = _parse_payload(event)
        payload.setdefault("observed_at", event.get("observed_at"))
        observations.append(payload)
    return observations


def _thresholds(config: Config) -> dict[str, int]:
    raw = config.thresholds if config else {}
    return {
        "low_reported_seeds": int(raw.get("low_reported_seeds", DEFAULT_LOW_REPORTED_SEEDS)),
        "healthy_reported_seeds": int(
            raw.get("healthy_reported_seeds", DEFAULT_HEALTHY_REPORTED_SEEDS)
        ),
    }


def _runtime_failed(observation: dict[str, Any]) -> bool:
    state = observation.get("qbittorrent_state")
    cls = states.classify(state)
    if cls == states.STALLED:
        return True
    if cls == states.ERROR:
        return True
    # Active download with zero peers and no progress is a runtime failure
    # symptom even before qBit flips to a stalled state classification.
    if states.is_active_download_state(state):
        peers = observation.get("actual_peers")
        dlspeed = observation.get("dlspeed")
        if peers is not None and peers == 0 and (dlspeed or 0) == 0:
            return True
    return False


def _runtime_healthy(observation: dict[str, Any]) -> bool:
    state = observation.get("qbittorrent_state")
    if states.is_seeding_state(state):
        return True
    if states.classify(state) in (states.COMPLETED, states.UPLOADING):
        return True
    return False


def _classify(
    observation: dict[str, Any],
    thresholds: dict[str, int],
) -> tuple[str, str, str, list[str]]:
    """Return (quality, confidence, decision_reason, evidence_messages)."""
    reported = observation.get("reported_seeds")
    actual_peers = observation.get("actual_peers")
    import_status = observation.get("import_status")
    runtime_state = observation.get("qbittorrent_state")
    runtime_healthy = _runtime_healthy(observation)
    runtime_failed = _runtime_failed(observation)

    messages: list[str] = []
    if reported is not None:
        messages.append(f"Reported seeds {reported}.")
    if actual_peers is not None:
        messages.append(f"Observed peers {actual_peers}.")
    if runtime_state:
        messages.append(f"qBittorrent state {runtime_state}.")
    if import_status:
        messages.append(f"Import status {import_status}.")

    # Bad Selection: indexer told us seeds were available, runtime says
    # otherwise, and the download cannot make progress.
    high_reported = (
        reported is not None and reported >= thresholds["healthy_reported_seeds"]
    )
    low_reported = (
        reported is not None and reported <= thresholds["low_reported_seeds"]
    )
    near_zero_peers = actual_peers is not None and actual_peers == 0

    if high_reported and near_zero_peers and runtime_failed:
        messages.append("Availability misrepresentation observed.")
        return (
            BAD,
            HIGH,
            "Availability misrepresentation observed.",
            messages,
        )
    if low_reported and near_zero_peers and runtime_failed:
        messages.append("Low-availability release stalled on runtime.")
        return (
            BAD,
            MEDIUM,
            "Low-availability release selected.",
            messages,
        )

    # Good Selection: ran the full pipeline cleanly.
    if (
        import_status == "Import Success"
        and runtime_healthy
    ):
        messages.append("Download completed, import succeeded, runtime healthy.")
        return (
            GOOD,
            HIGH,
            "Download completed, import succeeded, runtime healthy.",
            messages,
        )

    # Acceptable Selection: runtime healthy or completed but import telemetry
    # is missing -- the release itself looks fine, we just can't fully confirm.
    if runtime_healthy and import_status in (None, "Import Pending"):
        messages.append("Runtime healthy; awaiting import confirmation.")
        return (
            ACCEPTABLE,
            MEDIUM,
            "Runtime healthy; awaiting import confirmation.",
            messages,
        )

    # Questionable Selection: runtime metrics suggest the release is struggling
    # but not definitively bad -- stalls, low peers, metadata wait.
    if runtime_failed or near_zero_peers:
        if reported is None:
            messages.append("Indexer did not report seed count; cannot judge claim.")
        else:
            messages.append("Runtime is degraded relative to reported availability.")
        return (
            QUESTIONABLE,
            MEDIUM,
            "Runtime is degraded relative to reported availability.",
            messages,
        )

    # Unknown: lack of either runtime telemetry or import outcome.
    messages.append("Insufficient information to assess decision quality.")
    return (
        UNKNOWN,
        LOW,
        "Insufficient information to assess decision quality.",
        messages,
    )


def build_decision_assessments(config: Config) -> list[dict[str, Any]]:
    """Apply decision rules over persisted decision observations."""
    thresholds = _thresholds(config)
    assessments: list[dict[str, Any]] = []
    for observation in _latest_observations():
        quality, confidence, reason, messages = _classify(observation, thresholds)
        evidence = {
            "messages": messages,
            "reported_seeds": observation.get("reported_seeds"),
            "actual_peers": observation.get("actual_peers"),
            "actual_seeds": observation.get("actual_seeds"),
            "qbittorrent_state": observation.get("qbittorrent_state"),
            "import_status": observation.get("import_status"),
            "seerr_request_id": observation.get("seerr_request_id"),
            "torrent_hash": observation.get("torrent_hash"),
            "download_id": observation.get("download_id"),
            "candidates": observation.get("candidates") or [],
        }
        assessments.append(
            {
                "decision_id": observation.get("decision_id"),
                "media_id": observation.get("media_id"),
                "media_title": observation.get("media_title"),
                "selected_release": observation.get("selected_release"),
                "source_application": observation.get("source_application"),
                "source_indexer": observation.get("source_indexer"),
                "candidate_count": observation.get("candidate_count") or 0,
                "decision_reason": reason,
                "decision_quality": quality if quality in QUALITIES else UNKNOWN,
                "confidence": confidence,
                "evidence": evidence,
                "observed_at": observation.get("observed_at"),
            }
        )
    return assessments


def run_decisions(config: Config) -> int:
    assessments = build_decision_assessments(config)
    db.replace_decision_assessments(assessments)
    logger.info("Decision interpreter produced %d assessments", len(assessments))
    return len(assessments)


def summarize_decisions(assessments: list[dict[str, Any]]) -> dict[str, Any]:
    quality_counts = Counter(a.get("decision_quality") for a in assessments)
    indexer_counts = Counter(
        a.get("source_indexer") for a in assessments if a.get("source_indexer")
    )
    bad_by_indexer = Counter(
        a.get("source_indexer")
        for a in assessments
        if a.get("decision_quality") == BAD and a.get("source_indexer")
    )
    return {
        "total": len(assessments),
        "good": quality_counts.get(GOOD, 0),
        "acceptable": quality_counts.get(ACCEPTABLE, 0),
        "questionable": quality_counts.get(QUESTIONABLE, 0),
        "bad": quality_counts.get(BAD, 0),
        "unknown": quality_counts.get(UNKNOWN, 0),
        "top_indexers": indexer_counts.most_common(5),
        "top_bad_indexers": bad_by_indexer.most_common(5),
    }


def decisions_response(assessments: list[dict[str, Any]]) -> dict[str, Any]:
    summary = summarize_decisions(assessments)
    bad = [a for a in assessments if a.get("decision_quality") == BAD]
    questionable = [a for a in assessments if a.get("decision_quality") == QUESTIONABLE]
    return {
        "summary": summary,
        "assessments": assessments,
        "bad_decisions": bad,
        "questionable_decisions": questionable,
    }


def media_decision_response(
    media_id: str, assessments: list[dict[str, Any]]
) -> dict[str, Any]:
    matching = [a for a in assessments if str(a.get("media_id")) == str(media_id)]
    latest = matching[0] if matching else None
    return {
        "media_id": media_id,
        "decision_quality": latest.get("decision_quality") if latest else UNKNOWN,
        "decision_reason": latest.get("decision_reason") if latest else None,
        "selected_release": latest.get("selected_release") if latest else None,
        "source_application": latest.get("source_application") if latest else None,
        "source_indexer": latest.get("source_indexer") if latest else None,
        "candidate_count": latest.get("candidate_count") if latest else 0,
        "confidence": latest.get("confidence") if latest else LOW,
        "evidence": latest.get("evidence") if latest else {},
        "history": matching,
    }
