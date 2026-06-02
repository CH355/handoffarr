"""Cleanup evidence collector.

Builds read-only cleanup observations from persisted import, library, and
qBittorrent facts. This collector does not assign final cleanup status and never
modifies qBittorrent or the filesystem.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from .. import db
from ..config import Config
from . import qbittorrent

logger = logging.getLogger("handoffarr.collectors.cleanup")

SOURCE = "cleanup"
_WORD_RE = re.compile(r"[a-z0-9]+")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _torrent_size(payload: dict[str, Any]) -> int:
    for key in ("size", "total_size", "downloaded"):
        try:
            value = int(payload.get(key) or 0)
        except (TypeError, ValueError):
            value = 0
        if value > 0:
            return value
    return 0


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _cleanup_review_config(config: Config) -> dict[str, Any]:
    section = config.section("cleanup_review")
    return {
        "enabled": bool(section.get("enabled", True)),
        "max_file_checks_per_poll": int(section.get("max_file_checks_per_poll", 200)),
    }


def _build_observations(config: Config, observed_at: str) -> list[dict[str, Any]]:
    lookback_minutes = int(config.app.get("lookback_minutes", 120))
    since = (
        datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
    ).isoformat()

    qbit_events = _latest_by(
        db.events_for_source_since("qbittorrent", since),
        lambda e: e.get("torrent_hash"),
    )
    torrents_by_hash: dict[str, dict[str, Any]] = {}
    torrents_by_title: dict[str, dict[str, Any]] = {}
    for event in qbit_events:
        payload = _parse_payload(event)
        torrent_hash = str(event.get("torrent_hash") or payload.get("hash") or "").lower()
        if torrent_hash:
            torrents_by_hash[torrent_hash] = event
        norm = _normalize_title(payload.get("name") or event.get("title"))
        if norm and norm not in torrents_by_title:
            torrents_by_title[norm] = event

    libraries_by_media: dict[str, dict[str, Any]] = {}
    for artifact in db.all_library_artifacts():
        if artifact.get("media_id") is None:
            continue
        media_id = str(artifact.get("media_id"))
        current = libraries_by_media.get(media_id)
        if current is None or (
            bool(artifact.get("file_exists")) and not bool(current.get("file_exists"))
        ):
            libraries_by_media[media_id] = artifact

    observations: list[dict[str, Any]] = []
    for import_event in db.all_import_events():
        media_id = str(import_event.get("media_id") or import_event.get("import_id") or "")
        media_title = import_event.get("media_title")
        import_evidence = import_event.get("evidence") or {}
        torrent_hash = str(import_evidence.get("torrent_hash") or "").lower()
        torrent_event = torrents_by_hash.get(torrent_hash) if torrent_hash else None
        match_source = "torrent_hash" if torrent_event is not None else None
        if torrent_event is None:
            torrent_event = torrents_by_title.get(
                _normalize_title(media_title or import_event.get("source_path"))
            )
            match_source = "title_match" if torrent_event is not None else match_source

        torrent_payload = _parse_payload(torrent_event) if torrent_event else {}
        observed_hash = (
            str(torrent_event.get("torrent_hash") or torrent_payload.get("hash") or "").lower()
            if torrent_event
            else torrent_hash
        )
        library_artifact = libraries_by_media.get(media_id)
        observation = {
            "cleanup_id": f"cleanup:{observed_hash or media_id}",
            "media_id": media_id,
            "media_title": media_title,
            "source_application": import_event.get("source_application"),
            "torrent_hash": observed_hash or None,
            "download_id": import_evidence.get("download_id"),
            "import_status": import_event.get("import_status"),
            "import_timestamp": import_event.get("import_timestamp"),
            "library_status": None,
            "library_path": None,
            "library_file_exists": None,
            "torrent_present": torrent_event is not None,
            "torrent_state": torrent_payload.get("state"),
            "torrent_progress": torrent_payload.get("progress"),
            "retained_bytes": _torrent_size(torrent_payload) if torrent_event else 0,
            "download_path": torrent_payload.get("save_path"),
            "content_path": torrent_payload.get("content_path"),
            "torrent_name": torrent_payload.get("name"),
            "ratio": torrent_payload.get("ratio"),
            "seeding_time": torrent_payload.get("seeding_time"),
            "category": torrent_payload.get("category"),
            "tags": torrent_payload.get("tags"),
            "match_source": match_source,
            "observed_at": observed_at,
        }
        if library_artifact:
            observation.update(
                {
                    "library_status": library_artifact.get("library_status"),
                    "library_path": library_artifact.get("library_path"),
                    "library_file_exists": library_artifact.get("file_exists"),
                }
            )
        observations.append(observation)
    return observations


def _store_file_evidence(
    config: Config,
    observations: list[dict[str, Any]],
    observed_at: str,
) -> int:
    review_config = _cleanup_review_config(config)
    if not review_config["enabled"]:
        return 0

    hashes: list[str] = []
    seen: set[str] = set()
    for observation in sorted(
        observations,
        key=lambda item: _to_int(item.get("retained_bytes")),
        reverse=True,
    ):
        if not observation.get("torrent_present"):
            continue
        torrent_hash = str(observation.get("torrent_hash") or "").lower()
        if not torrent_hash or torrent_hash in seen:
            continue
        if _to_int(observation.get("retained_bytes")) <= 0:
            continue
        hashes.append(torrent_hash)
        seen.add(torrent_hash)
        if len(hashes) >= review_config["max_file_checks_per_poll"]:
            break

    if not hashes:
        return 0

    by_hash = {str(obs.get("torrent_hash") or "").lower(): obs for obs in observations}
    results = qbittorrent.fetch_torrent_files(config, hashes)
    stored = 0
    for torrent_hash, result in results.items():
        observation = by_hash.get(torrent_hash, {})
        files = result.get("files") if isinstance(result, dict) else []
        payload = {
            "torrent_hash": torrent_hash,
            "media_id": observation.get("media_id"),
            "media_title": observation.get("media_title"),
            "torrent_name": observation.get("torrent_name"),
            "save_path": observation.get("download_path"),
            "content_path": observation.get("content_path"),
            "library_path": observation.get("library_path"),
            "library_file_exists": observation.get("library_file_exists"),
            "ok": result.get("ok") if isinstance(result, dict) else False,
            "error": result.get("error") if isinstance(result, dict) else "no result",
            "files": files if isinstance(files, list) else [],
            "observed_at": observed_at,
        }
        db.insert_raw_event(
            source=SOURCE,
            event_type="file_evidence",
            external_id=f"cleanup-files:{torrent_hash}",
            title=observation.get("media_title"),
            torrent_hash=torrent_hash,
            download_id=None,
            payload=payload,
            observed_at=observed_at,
        )
        stored += 1
    return stored


def collect(config: Config) -> int:
    """Persist cleanup evidence observations through raw_events."""
    observed_at = _utcnow()
    stored = 0
    observations = _build_observations(config, observed_at)
    for observation in observations:
        db.insert_raw_event(
            source=SOURCE,
            event_type="observation",
            external_id=observation["cleanup_id"],
            title=observation.get("media_title"),
            torrent_hash=observation.get("torrent_hash"),
            download_id=None,
            payload=observation,
            observed_at=observed_at,
        )
        stored += 1
    stored += _store_file_evidence(config, observations, observed_at)
    logger.info("Cleanup collector stored %d observations", stored)
    return stored
