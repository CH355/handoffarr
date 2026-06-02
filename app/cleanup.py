"""Cleanup visibility interpretation.

Pure helpers over persisted cleanup observations. The collector records
evidence; this module classifies cleanup state and recoverable storage.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from . import db, states
from .config import Config
from .imports import IMPORT_SUCCESS
from .library import LIBRARY_PRESENT

CLEANUP_COMPLETED = "Cleanup Completed"
CLEANUP_PENDING = "Cleanup Pending"
CLEANUP_FAILED = "Cleanup Failed"
RETENTION_INTENTIONAL = "Retention Intentional"
CLEANUP_UNKNOWN = "Cleanup Unknown"
CLEANUP_STATUSES = {
    CLEANUP_COMPLETED,
    CLEANUP_PENDING,
    CLEANUP_FAILED,
    RETENTION_INTENTIONAL,
    CLEANUP_UNKNOWN,
}

DEFAULT_FAILURE_AFTER_HOURS = 24
RETENTION_WORDS = ("seed", "seeding", "retain", "retention", "keep", "archive")


def _parse_payload(event: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(event.get("payload_json") or "{}")
    except Exception:  # noqa: BLE001
        return {}


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:  # noqa: BLE001
        return None


def _latest_observations() -> list[dict[str, Any]]:
    events = [
        event
        for event in db.recent_events(source="cleanup", limit=2000)
        if event.get("event_type") == "observation"
    ]
    seen: set[str] = set()
    observations: list[dict[str, Any]] = []
    for event in events:
        key = event.get("external_id") or event.get("id")
        key = str(key)
        if key in seen:
            continue
        seen.add(key)
        payload = _parse_payload(event)
        payload.setdefault("observed_at", event.get("observed_at"))
        observations.append(payload)
    return observations


def _cleanup_config(config: Config) -> dict[str, Any]:
    cleanup = config.section("cleanup")
    thresholds = cleanup.get("thresholds") if isinstance(cleanup, dict) else {}
    thresholds = thresholds if isinstance(thresholds, dict) else {}
    return {
        "failure_after_hours": int(
            thresholds.get("failure_after_hours", DEFAULT_FAILURE_AFTER_HOURS)
        ),
        "retention_min_ratio": _to_float(thresholds.get("retention_min_ratio")),
    }


def _retention_evidence(observation: dict[str, Any], config: dict[str, Any]) -> str | None:
    state = str(observation.get("torrent_state") or "").lower()
    category = str(observation.get("category") or "").lower()
    tags = str(observation.get("tags") or "").lower()
    ratio = _to_float(observation.get("ratio"))
    min_ratio = config.get("retention_min_ratio")

    if state in {"uploading", "forcedup"}:
        return "Torrent is actively seeding."
    if any(word in category or word in tags for word in RETENTION_WORDS):
        return "Category or tags indicate retention policy."
    if min_ratio is not None and ratio is not None and ratio < min_ratio:
        return "Torrent has not met configured ratio requirement."
    return None


def _age_hours(observation: dict[str, Any]) -> float | None:
    imported_at = _parse_time(observation.get("import_timestamp"))
    if imported_at is None:
        return None
    return (datetime.now(timezone.utc) - imported_at).total_seconds() / 3600


def _classify(observation: dict[str, Any], config: dict[str, Any]) -> tuple[str, list[str]]:
    evidence: list[str] = []
    import_success = observation.get("import_status") == IMPORT_SUCCESS
    library_present = observation.get("library_status") == LIBRARY_PRESENT or bool(
        observation.get("library_file_exists")
    )
    torrent_present = bool(observation.get("torrent_present"))
    retained_bytes = _to_int(observation.get("retained_bytes"))

    if import_success:
        evidence.append("Import observed.")
    if library_present:
        evidence.append("Library verified.")

    if not import_success or not library_present:
        evidence.append("Insufficient information to classify cleanup.")
        return CLEANUP_UNKNOWN, evidence

    if not torrent_present:
        evidence.append("Torrent removed from qBittorrent.")
        return CLEANUP_COMPLETED, evidence

    evidence.append("Torrent retained.")
    retention_reason = _retention_evidence(observation, config)
    if retention_reason:
        evidence.append(retention_reason)
        return RETENTION_INTENTIONAL, evidence

    state = observation.get("torrent_state")
    completed = states.is_seeding_state(state) or states.classify(state) in (
        states.COMPLETED,
        states.UPLOADING,
    )
    if not completed:
        evidence.append("Torrent state is not a completed cleanup candidate.")
        return CLEANUP_UNKNOWN, evidence

    age = _age_hours(observation)
    if (
        retained_bytes > 0
        and age is not None
        and age >= config["failure_after_hours"]
    ):
        evidence.append(
            f"Torrent retained beyond {config['failure_after_hours']} hour cleanup threshold."
        )
        return CLEANUP_FAILED, evidence

    evidence.append("Completed torrent still exists.")
    return CLEANUP_PENDING, evidence


def build_cleanup_events(config: Config) -> list[dict[str, Any]]:
    """Build the current CleanupEvent snapshot from cleanup observations."""
    cleanup_config = _cleanup_config(config)
    cleanup_events: list[dict[str, Any]] = []
    for observation in _latest_observations():
        status, messages = _classify(observation, cleanup_config)
        retained_bytes = _to_int(observation.get("retained_bytes"))
        evidence = {
            "messages": messages,
            "import_status": observation.get("import_status"),
            "library_status": observation.get("library_status"),
            "library_path": observation.get("library_path"),
            "library_file_exists": observation.get("library_file_exists"),
            "torrent_present": observation.get("torrent_present"),
            "torrent_state": observation.get("torrent_state"),
            "download_path": observation.get("download_path"),
            "match_source": observation.get("match_source"),
            "retention": messages[-1] if status == RETENTION_INTENTIONAL else None,
        }
        cleanup_events.append(
            {
                "cleanup_id": observation.get("cleanup_id"),
                "media_id": observation.get("media_id"),
                "media_title": observation.get("media_title"),
                "source_application": observation.get("source_application"),
                "torrent_hash": observation.get("torrent_hash"),
                "cleanup_status": status,
                "retained_bytes": retained_bytes,
                "recoverable_bytes": (
                    retained_bytes
                    if status in {CLEANUP_PENDING, CLEANUP_FAILED}
                    else 0
                ),
                "cleanup_timestamp": observation.get("observed_at"),
                "evidence": evidence,
            }
        )
    return cleanup_events


def run_cleanup_visibility(config: Config) -> int:
    cleanup_events = build_cleanup_events(config)
    db.replace_cleanup_events(cleanup_events)
    return len(cleanup_events)


def summarize_cleanup(cleanup_events: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(event.get("cleanup_status") for event in cleanup_events)
    return {
        "completed": counts.get(CLEANUP_COMPLETED, 0),
        "pending": counts.get(CLEANUP_PENDING, 0),
        "failed": counts.get(CLEANUP_FAILED, 0),
        "intentional": counts.get(RETENTION_INTENTIONAL, 0),
        "unknown": counts.get(CLEANUP_UNKNOWN, 0),
        "total": len(cleanup_events),
        "total_recoverable_bytes": sum(
            _to_int(event.get("recoverable_bytes")) for event in cleanup_events
        ),
    }


def cleanup_response(cleanup_events: list[dict[str, Any]]) -> dict[str, Any]:
    by_status = {
        CLEANUP_COMPLETED: "completed",
        CLEANUP_PENDING: "pending",
        CLEANUP_FAILED: "failed",
        RETENTION_INTENTIONAL: "intentional",
        CLEANUP_UNKNOWN: "unknown",
    }
    response: dict[str, Any] = {"summary": summarize_cleanup(cleanup_events)}
    for status, key in by_status.items():
        response[key] = [
            event for event in cleanup_events if event.get("cleanup_status") == status
        ]
    response["top_cleanup_candidates"] = sorted(
        response["pending"] + response["failed"],
        key=lambda event: event.get("retained_bytes") or 0,
        reverse=True,
    )[:20]
    return response


def media_cleanup_response(media_id: str, cleanup_events: list[dict[str, Any]]) -> dict[str, Any]:
    matching = [
        event for event in cleanup_events if str(event.get("media_id")) == str(media_id)
    ]
    latest = matching[0] if matching else None
    return {
        "media_id": media_id,
        "cleanup_status": latest.get("cleanup_status") if latest else CLEANUP_UNKNOWN,
        "retained_bytes": latest.get("retained_bytes") if latest else 0,
        "recoverable_bytes": latest.get("recoverable_bytes") if latest else 0,
        "evidence": latest.get("evidence") if latest else {},
        "history": matching,
    }
