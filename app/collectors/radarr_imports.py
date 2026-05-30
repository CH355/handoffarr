"""Radarr import-history collector.

Reads Radarr history events and stores normalized import observations in
raw_events. The collector is read-only and performs no writes to Radarr.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .. import db
from ..config import Config

logger = logging.getLogger("handoffarr.collectors.radarr_imports")

SOURCE = "radarr"
MEDIA_TYPE = "movie"
SUCCESS_EVENT_HINTS = ("downloadfolderimported", "moviefileimported")
FAILURE_EVENT_HINTS = ("importfailed", "downloadfailed")
PATH_KEYS = ("droppedPath", "droppedRelPath", "sourcePath", "downloadPath", "path")
DESTINATION_KEYS = ("importedPath", "destinationPath", "movieFilePath")
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
    movie = record.get("movie")
    if isinstance(movie, dict):
        return movie.get("id") or record.get("movieId"), movie.get("title")
    return record.get("movieId"), record.get("sourceTitle")


def _file_path(record: dict[str, Any]) -> str | None:
    movie_file = record.get("movieFile")
    if isinstance(movie_file, dict) and movie_file.get("path"):
        return str(movie_file["path"])
    return None


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    data = _data(record)
    event_type = str(record.get("eventType") or "").lower()
    media_id, media_title = _media(record)
    status = "Import Success" if any(h in event_type for h in SUCCESS_EVENT_HINTS) else "Import Failed"
    return {
        "import_id": record.get("id"),
        "source_application": "Radarr",
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
    endpoint = svc.get("history_endpoint", "/api/v3/history")
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
        logger.debug("Radarr import collector skipped: %s", error)
        return 0

    stored = 0
    for record in records:
        event_type = str(record.get("eventType") or "").lower()
        if not any(h in event_type for h in SUCCESS_EVENT_HINTS + FAILURE_EVENT_HINTS):
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

    logger.info("Radarr import collector stored %d events", stored)
    return stored
