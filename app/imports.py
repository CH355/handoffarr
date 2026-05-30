"""Import visibility interpretation.

Pure helpers over persisted raw events. Collectors store read-only observations;
this module derives the current ImportEvent snapshot and API summaries.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from . import db, states
from .config import Config

IMPORT_SUCCESS = "Import Success"
IMPORT_FAILED = "Import Failed"
IMPORT_PENDING = "Import Pending"
IMPORT_STATUSES = {IMPORT_SUCCESS, IMPORT_FAILED, IMPORT_PENDING}

_WORD_RE = re.compile(r"[a-z0-9]+")


def _parse_payload(event: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(event.get("payload_json") or "{}")
    except Exception:  # noqa: BLE001
        return {}


def _normalize_title(title: str | None) -> str:
    if not title:
        return ""
    noise = {
        "1080p", "720p", "2160p", "4k", "x264", "x265", "h264", "h265",
        "hevc", "web", "webrip", "webdl", "bluray", "bdrip", "hdrip",
        "proper", "repack", "remux", "amzn", "nf", "dts", "aac", "ddp",
    }
    return " ".join(w for w in _WORD_RE.findall(title.lower()) if w not in noise)


def _latest_by(events: list[dict[str, Any]], key_fn) -> list[dict[str, Any]]:
    seen: set[str] = set()
    latest: list[dict[str, Any]] = []
    for event in events:
        key = key_fn(event)
        if key is None or key == "":
            key = event.get("id")
        key = str(key)
        if key in seen:
            continue
        seen.add(key)
        latest.append(event)
    return latest


def _is_complete_download(payload: dict[str, Any]) -> bool:
    state = payload.get("state")
    if states.is_seeding_state(state):
        return True
    try:
        return float(payload.get("progress") or 0) >= 1.0
    except (TypeError, ValueError):
        return False


def _event_from_import_observation(event: dict[str, Any]) -> dict[str, Any]:
    payload = _parse_payload(event)
    status = payload.get("import_status")
    if status not in IMPORT_STATUSES:
        status = IMPORT_FAILED if event.get("event_type") == "import_failed" else IMPORT_SUCCESS

    evidence = {
        "source": event.get("source"),
        "raw_event_id": event.get("id"),
        "event_type": payload.get("event_type") or event.get("event_type"),
        "download_id": payload.get("download_id") or event.get("download_id"),
        "torrent_hash": payload.get("torrent_hash") or event.get("torrent_hash"),
        "destination_path_present": bool(payload.get("destination_path")),
        "error": payload.get("error"),
        "message": (
            "Import event observed."
            if status == IMPORT_SUCCESS
            else "Import failure event observed."
        ),
    }
    return {
        "import_id": str(payload.get("import_id") or event.get("external_id")),
        "source_application": payload.get("source_application") or str(event.get("source", "")).title(),
        "media_type": payload.get("media_type"),
        "media_id": str(payload.get("media_id") or event.get("external_id")),
        "media_title": payload.get("media_title") or event.get("title"),
        "source_path": payload.get("source_path"),
        "destination_path": payload.get("destination_path"),
        "import_status": status,
        "import_timestamp": payload.get("import_timestamp") or event.get("observed_at"),
        "evidence": evidence,
    }


def build_import_events(config: Config) -> list[dict[str, Any]]:
    """Build the derived ImportEvent snapshot from raw observations."""
    lookback_minutes = int(config.app.get("lookback_minutes", 120))
    since = (
        datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
    ).isoformat()

    import_observations: list[dict[str, Any]] = []
    for source in ("sonarr", "radarr", "lidarr"):
        import_observations.extend(
            event
            for event in db.events_for_source_since(source, since)
            if str(event.get("event_type") or "").startswith("import_")
        )

    import_events = [
        _event_from_import_observation(event)
        for event in _latest_by(import_observations, lambda e: e.get("external_id"))
    ]

    hashes_with_import = {
        str((event.get("evidence") or {}).get("torrent_hash")).lower()
        for event in import_events
        if (event.get("evidence") or {}).get("torrent_hash")
    }
    titles_with_import = {
        _normalize_title(event.get("media_title") or event.get("source_path"))
        for event in import_events
    }

    qbit_events = db.events_for_source_since("qbittorrent", since)
    for event in _latest_by(qbit_events, lambda e: e.get("torrent_hash")):
        payload = _parse_payload(event)
        if not _is_complete_download(payload):
            continue
        torrent_hash = str(event.get("torrent_hash") or payload.get("hash") or "").lower()
        normalized_title = _normalize_title(payload.get("name") or event.get("title"))
        if torrent_hash in hashes_with_import or normalized_title in titles_with_import:
            continue
        media_id = torrent_hash or normalized_title or str(event.get("id"))
        import_events.append(
            {
                "import_id": f"pending:{media_id}",
                "source_application": "Unknown",
                "media_type": "unknown",
                "media_id": media_id,
                "media_title": payload.get("name") or event.get("title"),
                "source_path": payload.get("save_path"),
                "destination_path": None,
                "import_status": IMPORT_PENDING,
                "import_timestamp": event.get("observed_at"),
                "evidence": {
                    "source": "qbittorrent",
                    "raw_event_id": event.get("id"),
                    "torrent_hash": torrent_hash,
                    "state": payload.get("state"),
                    "progress": payload.get("progress"),
                    "message": "Download complete; no import event observed.",
                },
            }
        )

    return import_events


def run_import_visibility(config: Config) -> int:
    import_events = build_import_events(config)
    db.replace_import_events(import_events)
    return len(import_events)


def summarize_imports(import_events: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(event.get("import_status") for event in import_events)
    return {
        "success": counts.get(IMPORT_SUCCESS, 0),
        "failed": counts.get(IMPORT_FAILED, 0),
        "pending": counts.get(IMPORT_PENDING, 0),
        "total": len(import_events),
    }


def imports_response(import_events: list[dict[str, Any]]) -> dict[str, Any]:
    recent = sorted(
        import_events,
        key=lambda event: event.get("import_timestamp") or "",
        reverse=True,
    )
    return {
        "summary": summarize_imports(import_events),
        "counts": summarize_imports(import_events),
        "recent_imports": recent[:20],
        "failures": [
            event for event in recent if event.get("import_status") == IMPORT_FAILED
        ],
        "pending_imports": [
            event for event in recent if event.get("import_status") == IMPORT_PENDING
        ],
    }


def media_import_response(media_id: str, import_events: list[dict[str, Any]]) -> dict[str, Any]:
    history = [
        event for event in import_events if str(event.get("media_id")) == str(media_id)
    ]
    latest = history[0] if history else None
    return {
        "media_id": media_id,
        "import_status": latest.get("import_status") if latest else None,
        "history": history,
        "evidence": latest.get("evidence") if latest else {},
    }
