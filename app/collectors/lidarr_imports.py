"""Lidarr import-history collector.

Reads Lidarr history events and stores normalized import observations in
raw_events. The collector is read-only and performs no writes to Lidarr.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .. import db
from ..config import Config
from .import_history import (
    IMPORT_FAILURE_EVENTS,
    IMPORT_SUCCESS_EVENTS,
    canonical_event_type,
    classify_record,
    discard_reason,
    nested_path,
    resolve_event_type,
)

logger = logging.getLogger("handoffarr.collectors.lidarr_imports")

SOURCE = "lidarr"
MEDIA_TYPE = "music"
SUCCESS_EVENT_HINTS = tuple(
    IMPORT_SUCCESS_EVENTS | {"trackfileimported", "albumimported"}
)
FAILURE_EVENT_HINTS = tuple(IMPORT_FAILURE_EVENTS)
PATH_KEYS = ("droppedPath", "droppedRelPath", "sourcePath", "downloadPath", "path")
DESTINATION_KEYS = ("importedPath", "destinationPath", "trackFilePath", "filePath")
HASH_KEYS = ("torrentInfoHash", "torrentHash", "downloadHash")


def _data(record: dict[str, Any]) -> dict[str, Any]:
    data = record.get("data")
    return data if isinstance(data, dict) else {}


def _first(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None


def _media(record: dict[str, Any]) -> tuple[Any, str | None]:
    artist = record.get("artist")
    album = record.get("album")
    track = record.get("track")
    title_parts: list[str] = []
    if isinstance(artist, dict) and artist.get("artistName"):
        title_parts.append(str(artist["artistName"]))
    if isinstance(album, dict) and album.get("title"):
        title_parts.append(str(album["title"]))
    if isinstance(track, dict) and track.get("title"):
        title_parts.append(str(track["title"]))
    media_id = record.get("albumId") or record.get("artistId") or record.get("trackId")
    return media_id, " - ".join(title_parts) if title_parts else record.get("sourceTitle")


def _file_path(record: dict[str, Any]) -> str | None:
    return nested_path(record, ("trackFile", "file"))


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    data = _data(record)
    resolved = resolve_event_type(record, SOURCE)
    event_type = canonical_event_type(resolved)
    status, _basis = classify_record(record, SOURCE)
    if status is None:
        status = "Import Failed"
    media_id, media_title = _media(record)
    return {
        "import_id": record.get("id"),
        "source_application": "Lidarr",
        "media_type": MEDIA_TYPE,
        "media_id": media_id,
        "media_title": media_title,
        "source_path": _first(data, PATH_KEYS) or record.get("sourceTitle"),
        "destination_path": _first(data, DESTINATION_KEYS) or _file_path(record),
        "import_status": status,
        "import_timestamp": record.get("date"),
        "download_id": record.get("downloadId"),
        "torrent_hash": _first(data, HASH_KEYS),
        "error": data.get("reason") or data.get("message") or data.get("error"),
        "event_type": event_type,
        "raw": record,
    }


def fetch_history_raw(config: Config) -> tuple[bool, str | None, Any, list[dict[str, Any]]]:
    if not config.service_enabled(SOURCE):
        return False, "service disabled or not configured", None, []

    svc = config.service(SOURCE)
    base_url = str(svc.get("base_url", "")).rstrip("/")
    endpoint = svc.get("history_endpoint", "/api/v1/history")
    headers = {"Accept": "application/json"}
    if svc.get("api_key"):
        headers["X-Api-Key"] = svc["api_key"]
    params = {"page": 1, "pageSize": 100, "sortKey": "date", "sortDirection": "descending"}

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{base_url}{endpoint}", headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}", None, []

    records = data.get("records") if isinstance(data, dict) else data
    if not isinstance(records, list):
        records = []
    return True, None, data, [r for r in records if isinstance(r, dict)]


def collect(config: Config) -> int:
    ok, error, _raw, records = fetch_history_raw(config)
    if not ok:
        logger.debug("Lidarr import collector skipped: %s", error)
        return 0

    stored = 0
    for record in records:
        if discard_reason(record, SOURCE):
            continue
        norm = normalize_record(record)
        db.insert_raw_event(
            source=SOURCE,
            event_type=f"import_{norm['import_status'].split()[-1].lower()}",
            external_id=norm["import_id"],
            title=norm["media_title"],
            torrent_hash=str(norm["torrent_hash"]).lower() if norm.get("torrent_hash") else None,
            download_id=norm.get("download_id"),
            payload=norm,
            observed_at=None,
        )
        stored += 1

    logger.info("Lidarr import collector stored %d events", stored)
    return stored
