"""Library visibility interpretation.

Pure helpers over persisted raw events and import events. The collector observes
paths; this module derives LibraryArtifact snapshots and canonical statuses.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from . import db, states
from .config import Config
from .imports import IMPORT_SUCCESS

LIBRARY_PRESENT = "Library Present"
LIBRARY_MISSING = "Library Missing"
LIBRARY_UNKNOWN = "Library Unknown"
LIBRARY_STATUSES = {LIBRARY_PRESENT, LIBRARY_MISSING, LIBRARY_UNKNOWN}

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
        "season", "episode",
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


def _artifact_from_raw(event: dict[str, Any]) -> dict[str, Any]:
    payload = _parse_payload(event)
    evidence = payload.get("evidence")
    if not isinstance(evidence, dict):
        evidence = {}
    evidence.setdefault("raw_event_id", event.get("id"))
    evidence.setdefault("source", event.get("source"))
    return {
        "artifact_id": payload.get("artifact_id") or event.get("external_id"),
        "media_id": str(payload.get("media_id") or ""),
        "media_title": payload.get("media_title") or event.get("title"),
        "media_type": payload.get("media_type"),
        "library_path": payload.get("library_path"),
        "file_exists": bool(payload.get("file_exists")),
        "file_size": payload.get("file_size"),
        "source_application": payload.get("source_application"),
        "observed_at": payload.get("observed_at") or event.get("observed_at"),
        "evidence": evidence,
    }


def _status_for_artifact(
    artifact: dict[str, Any],
    import_event: dict[str, Any] | None,
) -> str:
    evidence = artifact.get("evidence") or {}
    if artifact.get("file_exists") and artifact.get("library_path"):
        return LIBRARY_PRESENT
    if (
        import_event
        and import_event.get("import_status") == IMPORT_SUCCESS
        and artifact.get("library_path")
        and evidence.get("path_verified") is False
    ):
        return LIBRARY_MISSING
    return LIBRARY_UNKNOWN


def _download_copy_present(
    artifact: dict[str, Any],
    import_event: dict[str, Any] | None,
    qbit_events: list[dict[str, Any]],
) -> tuple[bool, dict[str, Any]]:
    evidence = import_event.get("evidence") if import_event else {}
    evidence = evidence if isinstance(evidence, dict) else {}
    torrent_hash = str(evidence.get("torrent_hash") or "").lower()
    title = _normalize_title(artifact.get("media_title"))

    for event in qbit_events:
        payload = _parse_payload(event)
        event_hash = str(event.get("torrent_hash") or payload.get("hash") or "").lower()
        event_title = _normalize_title(payload.get("name") or event.get("title"))
        if torrent_hash and event_hash == torrent_hash:
            return True, {
                "source": "qbittorrent",
                "torrent_hash": event_hash,
                "state": payload.get("state"),
                "save_path": payload.get("save_path"),
                "message": "Download copy still present in qBittorrent.",
            }
        if title and event_title == title:
            return True, {
                "source": "qbittorrent",
                "torrent_hash": event_hash,
                "state": payload.get("state"),
                "save_path": payload.get("save_path"),
                "message": "Download copy matched by normalized title.",
            }
    return False, {}


def build_library_artifacts(config: Config) -> list[dict[str, Any]]:
    """Build the current LibraryArtifact snapshot from raw library events."""
    lookback_minutes = int(config.app.get("lookback_minutes", 120))
    since = (
        datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
    ).isoformat()

    raw_artifacts = [
        event
        for event in db.events_for_source_since("library", since)
        if event.get("event_type") == "artifact"
        and _parse_payload(event).get("import_status") == IMPORT_SUCCESS
    ]
    artifacts = [
        _artifact_from_raw(event)
        for event in _latest_by(raw_artifacts, lambda e: e.get("external_id"))
    ]
    artifacts_by_media = {
        str(artifact.get("media_id")): artifact
        for artifact in artifacts
        if artifact.get("media_id")
    }

    observed_at = datetime.now(timezone.utc).isoformat()
    for import_event in db.all_import_events():
        if import_event.get("import_status") != IMPORT_SUCCESS:
            continue
        media_id = str(import_event.get("media_id") or "")
        if not media_id or media_id in artifacts_by_media:
            continue
        artifacts.append(
            {
                "artifact_id": f"library:unknown:{media_id}",
                "media_id": media_id,
                "media_title": import_event.get("media_title"),
                "media_type": import_event.get("media_type"),
                "library_path": import_event.get("destination_path"),
                "file_exists": False,
                "file_size": None,
                "source_application": import_event.get("source_application"),
                "observed_at": observed_at,
                "evidence": {
                    "source": "import_events",
                    "import_id": import_event.get("import_id"),
                    "import_status": import_event.get("import_status"),
                    "message": "Import event exists; no library observation available.",
                },
            }
        )

    return artifacts


def run_library_visibility(config: Config) -> int:
    artifacts = build_library_artifacts(config)
    db.replace_library_artifacts(artifacts)
    return len(artifacts)


def enrich_library_artifacts(
    artifacts: list[dict[str, Any]],
    config: Config,
) -> list[dict[str, Any]]:
    lookback_minutes = int(config.app.get("lookback_minutes", 120))
    since = (
        datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
    ).isoformat()
    imports_by_media = {
        str(event.get("media_id")): event for event in db.all_import_events()
    }
    qbit_events = _latest_by(
        db.events_for_source_since("qbittorrent", since),
        lambda e: e.get("torrent_hash"),
    )

    enriched: list[dict[str, Any]] = []
    for artifact in artifacts:
        item = dict(artifact)
        import_event = imports_by_media.get(str(item.get("media_id")))
        status = _status_for_artifact(item, import_event)
        download_present, download_evidence = _download_copy_present(
            item, import_event, qbit_events
        )
        import_success = bool(
            import_event and import_event.get("import_status") == IMPORT_SUCCESS
        )
        item["library_status"] = status
        item["download_copy_present"] = download_present
        item["potential_cleanup_candidate"] = (
            import_success and status == LIBRARY_PRESENT and download_present
        )
        item["import_status"] = import_event.get("import_status") if import_event else None
        item["paths"] = {
            "library_path": item.get("library_path"),
            "download_path": download_evidence.get("save_path"),
        }
        evidence = dict(item.get("evidence") or {})
        if import_event:
            evidence["import"] = {
                "import_id": import_event.get("import_id"),
                "import_status": import_event.get("import_status"),
                "message": "Import event observed.",
            }
        if status == LIBRARY_PRESENT:
            evidence["library"] = "Library file verified."
        elif status == LIBRARY_MISSING:
            evidence["library"] = "Import event exists; expected library file not found."
        else:
            evidence["library"] = "Insufficient information to verify library file."
        if download_evidence:
            evidence["download_copy"] = download_evidence
        item["evidence"] = evidence
        enriched.append(item)
    return enriched


def summarize_library(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(artifact.get("library_status") for artifact in artifacts)
    return {
        "present": counts.get(LIBRARY_PRESENT, 0),
        "missing": counts.get(LIBRARY_MISSING, 0),
        "unknown": counts.get(LIBRARY_UNKNOWN, 0),
        "potential_cleanup_candidates": sum(
            1 for artifact in artifacts if artifact.get("potential_cleanup_candidate")
        ),
        "total": len(artifacts),
    }


def library_response(
    artifacts: list[dict[str, Any]],
    config: Config,
) -> dict[str, Any]:
    enriched = enrich_library_artifacts(artifacts, config)
    return {
        "summary": summarize_library(enriched),
        "present": [
            item for item in enriched if item.get("library_status") == LIBRARY_PRESENT
        ],
        "missing": [
            item for item in enriched if item.get("library_status") == LIBRARY_MISSING
        ],
        "unknown": [
            item for item in enriched if item.get("library_status") == LIBRARY_UNKNOWN
        ],
        "potential_cleanup_candidates": [
            item for item in enriched if item.get("potential_cleanup_candidate")
        ],
        "artifacts": enriched,
    }


def media_library_response(
    media_id: str,
    artifacts: list[dict[str, Any]],
    config: Config,
) -> dict[str, Any]:
    enriched = enrich_library_artifacts(artifacts, config)
    matching = [item for item in enriched if str(item.get("media_id")) == str(media_id)]
    latest = matching[0] if matching else None
    return {
        "media_id": media_id,
        "library_artifact": latest,
        "library_status": latest.get("library_status") if latest else LIBRARY_UNKNOWN,
        "paths": latest.get("paths") if latest else {},
        "evidence": latest.get("evidence") if latest else {},
    }
