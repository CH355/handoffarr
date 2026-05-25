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


TITLE_KEYS = ("title", "name", "originalTitle", "originalName")
REQUESTED_AT_KEYS = ("createdAt", "requestedDate", "updatedAt")


def _media_title(media: dict[str, Any]) -> str | None:
    if not isinstance(media, dict):
        return None
    # Overseerr/Jellyseerr expose titles in a few possible places.
    for key in TITLE_KEYS:
        value = media.get(key)
        if value:
            return str(value)
    return None


def _normalize_request(req: dict[str, Any]) -> dict[str, Any]:
    """Project a raw Seerr request into our normalized shape."""
    media = req.get("media") or {}
    title = _media_title(media) or req.get("title")
    requested_at = None
    for key in REQUESTED_AT_KEYS:
        if req.get(key):
            requested_at = req.get(key)
            break
    return {
        "id": req.get("id"),
        "status": req.get("status"),
        "title": title,
        "requested_at": requested_at,
    }


def fetch_requests_raw(
    config: Config,
) -> tuple[bool, str | None, Any, list[dict[str, Any]]]:
    """Read-only fetch of Seerr requests. Returns (ok, error, raw, results)."""
    if not config.service_enabled(SOURCE):
        return False, "service disabled or not configured", None, []

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
        return False, f"{type(exc).__name__}: {exc}", None, []

    # Response may be {"results": [...]} or a bare list.
    if isinstance(data, dict):
        results = data.get("results") or data.get("requests") or []
    elif isinstance(data, list):
        results = data
    else:
        results = []
    return True, None, data, [r for r in results if isinstance(r, dict)]


def collect(config: Config) -> int:
    """Poll Seerr requests. Returns the number of events stored."""
    if not config.service_enabled(SOURCE):
        logger.debug("Seerr collector disabled or not configured")
        return 0

    ok, error, _raw, results = fetch_requests_raw(config)
    if not ok:
        logger.warning("Seerr poll failed: %s", error)
        return 0

    stored = 0
    for req in results:
        try:
            norm = _normalize_request(req)
            db.insert_raw_event(
                source=SOURCE,
                event_type="request",
                external_id=norm["id"],
                title=norm["title"],
                torrent_hash=None,
                download_id=None,
                payload=norm,
                observed_at=None,
            )
            stored += 1
        except Exception as exc:  # noqa: BLE001
            logger.debug("Skipping malformed Seerr request: %s", exc)

    logger.info("Seerr collector stored %d events", stored)
    return stored


def inspect(config: Config) -> dict[str, Any]:
    """Debug view: raw payload, normalized requests, extraction diagnostics and
    missing-field warnings for the current Seerr request list."""
    svc = config.service(SOURCE)
    ok, error, raw, results = fetch_requests_raw(config)

    normalized: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    warnings: list[str] = []

    for req in results:
        norm = _normalize_request(req)
        normalized.append(norm)

        media = req.get("media") or {}
        title_key = next((k for k in TITLE_KEYS if media.get(k)), None)
        requested_key = next((k for k in REQUESTED_AT_KEYS if req.get(k)), None)
        diagnostics.append(
            {
                "id": norm["id"],
                "title_source_key": title_key,
                "requested_at_source_key": requested_key,
                "has_media_object": isinstance(req.get("media"), dict),
                "top_level_keys": sorted(req.keys()),
            }
        )

        label = norm["title"] or norm["id"]
        if norm["title"] is None:
            warnings.append(
                f"request {norm['id']}: no title "
                f"(checked media.{{{', '.join(TITLE_KEYS)}}} and top-level title)"
            )
        if norm["requested_at"] is None:
            warnings.append(
                f"request {norm['id']} ({label}): no timestamp "
                f"(checked {', '.join(REQUESTED_AT_KEYS)})"
            )
        if not isinstance(req.get("media"), dict):
            warnings.append(f"request {norm['id']} ({label}): no media object")

    return {
        "service": SOURCE,
        "enabled": config.service_enabled(SOURCE),
        "url": f"{str(svc.get('base_url', '')).rstrip('/')}"
        f"{svc.get('request_endpoint', '/api/v1/request')}",
        "ok": ok,
        "error": error,
        "request_count": len(results),
        "raw": raw,
        "normalized": normalized,
        "diagnostics": diagnostics,
        "warnings": warnings,
    }
