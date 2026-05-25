"""Seerr / Jellyseerr / Overseerr request collector.

Polls recent media requests (read-only) and stores them as raw events. Designed
to tolerate the field-naming differences between Overseerr and Jellyseerr and to
never crash the app when the service is disabled or unreachable.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .. import db
from ..config import Config

logger = logging.getLogger("handoffarr.collectors.seerr")

SOURCE = "seerr"


def _media_title(media: dict[str, Any]) -> str | None:
    if not isinstance(media, dict):
        return None
    # Overseerr/Jellyseerr expose titles in a few possible places.
    for key in ("title", "name", "originalTitle", "originalName"):
        value = media.get(key)
        if value:
            return str(value)
    return None


def collect(config: Config) -> int:
    """Poll Seerr requests. Returns the number of events stored."""
    if not config.service_enabled(SOURCE):
        logger.debug("Seerr collector disabled or not configured")
        return 0

    svc = config.service(SOURCE)
    base_url = str(svc.get("base_url", "")).rstrip("/")
    api_key = svc.get("api_key")
    endpoint = svc.get("request_endpoint", "/api/v1/request")
    url = f"{base_url}{endpoint}"

    headers = {"Accept": "application/json"}
    if api_key:
        headers["X-Api-Key"] = api_key

    # Ask for the most recent requests; Overseerr-style pagination params.
    params = {"take": 50, "sort": "added"}

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Seerr poll failed (%s): %s", url, exc)
        return 0

    # Response may be {"results": [...]} or a bare list.
    if isinstance(data, dict):
        results = data.get("results") or data.get("requests") or []
    elif isinstance(data, list):
        results = data
    else:
        results = []

    stored = 0
    for req in results:
        if not isinstance(req, dict):
            continue
        try:
            request_id = req.get("id")
            status = req.get("status")
            media = req.get("media") or {}
            title = _media_title(media) or req.get("title")
            requested_at = (
                req.get("createdAt")
                or req.get("requestedDate")
                or req.get("updatedAt")
            )
            db.insert_raw_event(
                source=SOURCE,
                event_type="request",
                external_id=request_id,
                title=title,
                torrent_hash=None,
                download_id=None,
                payload={
                    "id": request_id,
                    "status": status,
                    "title": title,
                    "requested_at": requested_at,
                },
                observed_at=None,
            )
            stored += 1
        except Exception as exc:  # noqa: BLE001
            logger.debug("Skipping malformed Seerr request: %s", exc)

    logger.info("Seerr collector stored %d events", stored)
    return stored
