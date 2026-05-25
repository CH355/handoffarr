"""Radarr history collector.

Polls recent Radarr history (read-only), focusing on grab / release-selected
events so we can see which release Radarr handed off and what it reported about
it. Read-only: nothing in Radarr is modified.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .. import db
from ..config import Config

logger = logging.getLogger("handoffarr.collectors.radarr")

SOURCE = "radarr"

# Radarr event types that represent a release being selected / grabbed.
GRAB_EVENT_TYPES = {"grabbed", "downloadfolderimported", "movieFileImported"}


def _to_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _extract_seeds(record: dict[str, Any]) -> int | None:
    data = record.get("data") or {}
    for key in ("seeders", "Seeders", "seedCount"):
        seeds = _to_int(data.get(key))
        if seeds is not None:
            return seeds
    return None


def _extract_indexer(record: dict[str, Any]) -> str | None:
    data = record.get("data") or {}
    for key in ("indexer", "Indexer"):
        value = data.get(key)
        if value:
            return str(value)
    return None


def collect(config: Config) -> int:
    """Poll Radarr history. Returns the number of events stored."""
    if not config.service_enabled(SOURCE):
        logger.debug("Radarr collector disabled or not configured")
        return 0

    svc = config.service(SOURCE)
    base_url = str(svc.get("base_url", "")).rstrip("/")
    api_key = svc.get("api_key")
    endpoint = svc.get("history_endpoint", "/api/v3/history")
    url = f"{base_url}{endpoint}"

    headers = {"Accept": "application/json"}
    if api_key:
        headers["X-Api-Key"] = api_key

    params = {
        "page": 1,
        "pageSize": 50,
        "sortKey": "date",
        "sortDirection": "descending",
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Radarr poll failed (%s): %s", url, exc)
        return 0

    if isinstance(data, dict):
        records = data.get("records") or []
    elif isinstance(data, list):
        records = data
    else:
        records = []

    stored = 0
    for record in records:
        if not isinstance(record, dict):
            continue
        try:
            event_type = str(record.get("eventType", "")).lower()
            # Keep grab-style events; tolerate unknown casing/types.
            if event_type and event_type not in {e.lower() for e in GRAB_EVENT_TYPES}:
                # Still store grabbed; skip pure noise like "movieFileDeleted".
                if "grab" not in event_type:
                    continue

            history_id = record.get("id")
            source_title = record.get("sourceTitle")
            download_id = record.get("downloadId")
            data_blob = record.get("data") or {}
            torrent_hash = (
                data_blob.get("torrentInfoHash")
                or data_blob.get("torrentHash")
                or data_blob.get("downloadHash")
            )
            movie = record.get("movie") or {}
            movie_title = movie.get("title") if isinstance(movie, dict) else None

            db.insert_raw_event(
                source=SOURCE,
                event_type=event_type or "history",
                external_id=history_id,
                title=movie_title or source_title,
                torrent_hash=str(torrent_hash).lower() if torrent_hash else None,
                download_id=download_id,
                payload={
                    "id": history_id,
                    "eventType": event_type,
                    "sourceTitle": source_title,
                    "downloadId": download_id,
                    "indexer": _extract_indexer(record),
                    "reported_seeds": _extract_seeds(record),
                    "movie_title": movie_title,
                    "torrent_hash": torrent_hash,
                },
                observed_at=None,
            )
            stored += 1
        except Exception as exc:  # noqa: BLE001
            logger.debug("Skipping malformed Radarr record: %s", exc)

    logger.info("Radarr collector stored %d events", stored)
    return stored
