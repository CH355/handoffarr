"""Radarr history collector.

Polls recent Radarr history (read-only), focusing on grab / release-selected
events so we can see which release Radarr handed off and what it reported about
it. Read-only: nothing in Radarr is modified.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

import httpx

from .. import db
from ..config import Config

logger = logging.getLogger("handoffarr.collectors.radarr")

SOURCE = "radarr"

# Radarr event types that represent a release being selected / grabbed.
GRAB_EVENT_TYPES = {"grabbed", "downloadfolderimported", "movieFileImported"}

# Keys we probe, in priority order, when extracting fields from a history
# record's nested ``data`` blob. Exposed so the debug endpoints can report which
# key actually supplied a value (or that none did).
SEED_KEYS = ("seeders", "Seeders", "seedCount")
INDEXER_KEYS = ("indexer", "Indexer")
HASH_KEYS = ("torrentInfoHash", "torrentHash", "downloadHash")


def _to_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _extract_with_key(
    data: dict[str, Any], keys: tuple[str, ...], *, as_int: bool = False
) -> tuple[Any, str | None]:
    """Return (value, source_key) for the first present key, else (None, None)."""
    for key in keys:
        raw = data.get(key)
        value = _to_int(raw) if as_int else (str(raw) if raw else None)
        if value is not None:
            return value, key
    return None, None


def _extract_seeds(record: dict[str, Any]) -> int | None:
    value, _ = _extract_with_key(record.get("data") or {}, SEED_KEYS, as_int=True)
    return value


def _extract_indexer(record: dict[str, Any]) -> str | None:
    value, _ = _extract_with_key(record.get("data") or {}, INDEXER_KEYS)
    return value


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Project a raw Radarr history record into our normalized shape."""
    data_blob = record.get("data") or {}
    torrent_hash, _ = _extract_with_key(data_blob, HASH_KEYS)
    movie = record.get("movie") or {}
    movie_title = movie.get("title") if isinstance(movie, dict) else None
    return {
        "id": record.get("id"),
        "eventType": str(record.get("eventType", "")).lower(),
        "sourceTitle": record.get("sourceTitle"),
        "downloadId": record.get("downloadId"),
        "indexer": _extract_indexer(record),
        "reported_seeds": _extract_seeds(record),
        "movie_title": movie_title,
        "torrent_hash": torrent_hash,
    }


def fetch_history_raw(
    config: Config,
) -> tuple[bool, str | None, Any, list[dict[str, Any]]]:
    """Read-only fetch of Radarr history. Returns (ok, error, raw, records)."""
    if not config.service_enabled(SOURCE):
        return False, "service disabled or not configured", None, []

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
        return False, f"{type(exc).__name__}: {exc}", None, []

    if isinstance(data, dict):
        records = data.get("records") or []
    elif isinstance(data, list):
        records = data
    else:
        records = []
    return True, None, data, [r for r in records if isinstance(r, dict)]


def collect(config: Config) -> int:
    """Poll Radarr history. Returns the number of events stored."""
    if not config.service_enabled(SOURCE):
        logger.debug("Radarr collector disabled or not configured")
        return 0

    ok, error, _raw, records = fetch_history_raw(config)
    if not ok:
        logger.warning("Radarr poll failed: %s", error)
        return 0

    stored = 0
    for record in records:
        try:
            norm = _normalize_record(record)
            event_type = norm["eventType"]
            # Keep grab-style events; tolerate unknown casing/types.
            if event_type and event_type not in {e.lower() for e in GRAB_EVENT_TYPES}:
                # Still store grabbed; skip pure noise like "movieFileDeleted".
                if "grab" not in event_type:
                    continue

            torrent_hash = norm["torrent_hash"]
            db.insert_raw_event(
                source=SOURCE,
                event_type=event_type or "history",
                external_id=norm["id"],
                title=norm["movie_title"] or norm["sourceTitle"],
                torrent_hash=str(torrent_hash).lower() if torrent_hash else None,
                download_id=norm["downloadId"],
                payload=norm,
                observed_at=None,
            )
            stored += 1
        except Exception as exc:  # noqa: BLE001
            logger.debug("Skipping malformed Radarr record: %s", exc)

    logger.info("Radarr collector stored %d events", stored)
    return stored


def inspect(config: Config) -> dict[str, Any]:
    """Debug view: raw payload, normalized records, extraction diagnostics and
    missing-field warnings for the current Radarr history."""
    svc = config.service(SOURCE)
    ok, error, raw, records = fetch_history_raw(config)

    normalized: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    warnings: list[str] = []

    for record in records:
        norm = _normalize_record(record)
        normalized.append(norm)

        data_blob = record.get("data") or {}
        _, seed_key = _extract_with_key(data_blob, SEED_KEYS, as_int=True)
        _, hash_key = _extract_with_key(data_blob, HASH_KEYS)
        _, indexer_key = _extract_with_key(data_blob, INDEXER_KEYS)
        diagnostics.append(
            {
                "id": norm["id"],
                "eventType": norm["eventType"],
                "seed_source_key": seed_key,
                "hash_source_key": hash_key,
                "indexer_source_key": indexer_key,
                "data_keys": sorted(data_blob.keys())
                if isinstance(data_blob, dict)
                else [],
            }
        )

        label = norm["sourceTitle"] or norm["movie_title"] or norm["id"]
        if norm["torrent_hash"] is None:
            warnings.append(
                f"record {norm['id']} ({label}): no torrent hash "
                f"(checked {', '.join(HASH_KEYS)})"
            )
        if norm["reported_seeds"] is None:
            warnings.append(
                f"record {norm['id']} ({label}): no seed count "
                f"(checked {', '.join(SEED_KEYS)})"
            )
        if norm["indexer"] is None:
            warnings.append(f"record {norm['id']} ({label}): no indexer reported")

    return {
        "service": SOURCE,
        "enabled": config.service_enabled(SOURCE),
        "url": f"{str(svc.get('base_url', '')).rstrip('/')}"
        f"{svc.get('history_endpoint', '/api/v3/history')}",
        "ok": ok,
        "error": error,
        "record_count": len(records),
        "raw": raw,
        "normalized": normalized,
        "diagnostics": diagnostics,
        "warnings": warnings,
    }


def discover_fields(config: Config) -> dict[str, Any]:
    """Debug view: every key seen across Radarr history records (top-level and
    nested ``data``), how often each appears, and seed-related candidates."""
    ok, error, _raw, records = fetch_history_raw(config)

    top_level: Counter[str] = Counter()
    data_level: Counter[str] = Counter()
    seed_candidates: dict[str, dict[str, Any]] = {}

    def _note_candidate(name: str, value: Any) -> None:
        entry = seed_candidates.setdefault(name, {"count": 0, "sample_values": []})
        entry["count"] += 1
        if value is not None and len(entry["sample_values"]) < 5:
            sample = str(value)
            if sample not in entry["sample_values"]:
                entry["sample_values"].append(sample)

    for record in records:
        for key, value in record.items():
            top_level[key] += 1
            if "seed" in key.lower():
                _note_candidate(key, value)
        data_blob = record.get("data")
        if isinstance(data_blob, dict):
            for key, value in data_blob.items():
                data_level[key] += 1
                if "seed" in key.lower():
                    _note_candidate(f"data.{key}", value)

    def _sorted(counter: Counter[str]) -> dict[str, int]:
        return dict(counter.most_common())

    return {
        "service": SOURCE,
        "ok": ok,
        "error": error,
        "record_count": len(records),
        "top_level_keys": _sorted(top_level),
        "data_keys": _sorted(data_level),
        "seed_candidate_fields": seed_candidates,
    }
