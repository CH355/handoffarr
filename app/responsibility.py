"""Responsibility and storage interpretation.

Pure helpers over persisted observations. Collectors gather facts, db.py stores
them, and this module derives the current storage answer without doing I/O.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from . import db, states
from .config import Config

logger = logging.getLogger("handoffarr.responsibility")

DEFAULT_STORAGE_THRESHOLDS = {
    "critical_free_bytes": 1073741824,
    "warning_free_bytes": 10737418240,
    "completed_torrent_count": 25,
    "retained_bytes": 107374182400,
}


def _parse_payload(event: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(event.get("payload_json") or "{}")
    except Exception:  # noqa: BLE001
        return {}


def _to_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _latest_by(events: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    seen: set[str] = set()
    latest: list[dict[str, Any]] = []
    for event in events:
        value = event.get(key)
        if value is None:
            value = str(event.get("id"))
        value = str(value)
        if value in seen:
            continue
        seen.add(value)
        latest.append(event)
    return latest


def _storage_thresholds(config: Config) -> dict[str, int]:
    storage = config.section("storage")
    configured = storage.get("thresholds") or {}
    thresholds = dict(DEFAULT_STORAGE_THRESHOLDS)
    if isinstance(configured, dict):
        thresholds.update(
            {key: int(value) for key, value in configured.items() if value is not None}
        )
    return thresholds


def _torrent_size(payload: dict[str, Any]) -> int:
    for key in ("size", "total_size", "downloaded"):
        value = _to_int(payload.get(key))
        if value is not None and value > 0:
            return value
    return 0


def _is_completed_torrent(payload: dict[str, Any]) -> bool:
    state = payload.get("state")
    progress = payload.get("progress")
    if states.is_seeding_state(state):
        return True
    if states.classify(state) in (states.COMPLETED, states.UPLOADING):
        return True
    try:
        return float(progress) >= 1.0
    except (TypeError, ValueError):
        return False


def build_storage_summary(config: Config) -> dict[str, Any]:
    """Return storage visibility derived from persisted raw_events."""
    lookback_minutes = int(config.app.get("lookback_minutes", 120))
    since = (
        datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
    ).isoformat()
    thresholds = _storage_thresholds(config)

    qbit_events = db.events_for_source_since("qbittorrent", since)
    fs_events = db.events_for_source_since("filesystem", since)

    latest_torrents = _latest_by(qbit_events, "torrent_hash")
    retained_torrents: list[dict[str, Any]] = []
    for event in latest_torrents:
        payload = _parse_payload(event)
        if not _is_completed_torrent(payload):
            continue
        size_bytes = _torrent_size(payload)
        retained_torrents.append(
            {
                "hash": event.get("torrent_hash"),
                "name": payload.get("name") or event.get("title"),
                "state": payload.get("state"),
                "size_bytes": size_bytes,
                "save_path": payload.get("save_path"),
                "category": payload.get("category"),
                "tags": payload.get("tags"),
                "completion_on": payload.get("completion_on"),
            }
        )

    volume_events = [e for e in fs_events if e.get("event_type") == "volume"]
    artifact_events = [e for e in fs_events if e.get("event_type") == "artifact"]
    volumes = [_parse_payload(e) for e in _latest_by(volume_events, "external_id")]
    artifacts = [_parse_payload(e) for e in _latest_by(artifact_events, "external_id")]

    free_values = [
        value
        for value in (_to_int(v.get("free_bytes")) for v in volumes)
        if value is not None
    ]
    total_values = [
        value
        for value in (_to_int(v.get("total_bytes")) for v in volumes)
        if value is not None
    ]
    used_values = [
        value
        for value in (_to_int(v.get("used_bytes")) for v in volumes)
        if value is not None
    ]

    free_bytes = min(free_values) if free_values else None
    total_bytes = sum(total_values) if total_values else None
    used_bytes = sum(used_values) if used_values else None
    retained_bytes = sum(t["size_bytes"] for t in retained_torrents)
    completed_count = len(retained_torrents)

    if free_bytes is None:
        health = "unknown"
    elif free_bytes < thresholds["critical_free_bytes"]:
        health = "critical"
    elif free_bytes < thresholds["warning_free_bytes"]:
        health = "warning"
    else:
        health = "healthy"

    top_contributors = sorted(
        retained_torrents, key=lambda item: item["size_bytes"], reverse=True
    )[:10]

    return {
        "summary": {
            "health": health,
            "free_bytes": free_bytes,
            "total_bytes": total_bytes,
            "used_bytes": used_bytes,
            "retained_bytes": retained_bytes,
            "completed_torrent_bytes": retained_bytes,
            "completed_torrent_count": completed_count,
            "warning_free_bytes": thresholds["warning_free_bytes"],
            "critical_free_bytes": thresholds["critical_free_bytes"],
            "retained_bytes_threshold": thresholds["retained_bytes"],
            "completed_torrent_threshold": thresholds["completed_torrent_count"],
        },
        "volumes": volumes,
        "artifacts": artifacts,
        "retained_torrents": top_contributors,
    }


def build_responsibility_assessments(config: Config) -> list[dict[str, Any]]:
    """Apply the MVP responsibility rule set."""
    storage = build_storage_summary(config)
    summary = storage["summary"]
    observed_at = datetime.now(timezone.utc).isoformat()

    completed_count = summary.get("completed_torrent_count") or 0
    retained_bytes = summary.get("retained_bytes") or 0
    free_bytes = summary.get("free_bytes")
    warning_free_bytes = summary.get("warning_free_bytes")

    if (
        completed_count > summary.get("completed_torrent_threshold", 0)
        and retained_bytes > summary.get("retained_bytes_threshold", 0)
        and free_bytes is not None
        and warning_free_bytes is not None
        and free_bytes < warning_free_bytes
    ):
        hour_bucket = observed_at[:13]
        return [
            {
                "assessment_id": f"storage:cleanup-subsystem:{hour_bucket}",
                "lifecycle_stage": "Storage",
                "diagnosis": "Storage Failure",
                "responsible_domain": "Cleanup Subsystem",
                "confidence": "High",
                "evidence": [
                    {
                        "source": "qbittorrent",
                        "field": "completed_torrents",
                        "value": completed_count,
                    },
                    {
                        "source": "qbittorrent",
                        "field": "retained_bytes",
                        "value": retained_bytes,
                    },
                    {
                        "source": "filesystem",
                        "field": "free_bytes",
                        "value": free_bytes,
                    },
                ],
                "impact": {
                    "retained_bytes": retained_bytes,
                    "affected_torrents": completed_count,
                    "free_bytes": free_bytes,
                },
                "recommended_action": (
                    "Review cleanup policy and completed torrent retention."
                ),
                "observed_at": observed_at,
            }
        ]

    return []


def run_responsibility(config: Config) -> int:
    assessments = build_responsibility_assessments(config)
    db.replace_responsibility_assessments(assessments)
    logger.info("Responsibility produced %d assessments", len(assessments))
    return len(assessments)


def summarize_assessments(assessments: list[dict[str, Any]]) -> dict[str, Any]:
    top = assessments[0] if assessments else None
    return {
        "top_diagnosis": top.get("diagnosis") if top else None,
        "top_responsible_domain": top.get("responsible_domain") if top else None,
        "assessment_count": len(assessments),
    }
