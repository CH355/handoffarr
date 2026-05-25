"""qBittorrent collector.

Logs in via the Web API, maintains a cookie session, and polls the current
torrent list (read-only). Optionally fetches per-torrent trackers. Nothing is
added, removed, paused, resumed, or otherwise modified.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

import httpx

from .. import db, states
from ..config import Config

logger = logging.getLogger("handoffarr.collectors.qbittorrent")

SOURCE = "qbittorrent"


def _login(client: httpx.Client, base_url: str, username: str, password: str) -> bool:
    try:
        resp = client.post(
            f"{base_url}/api/v2/auth/login",
            data={"username": username, "password": password},
            headers={"Referer": base_url},
        )
        resp.raise_for_status()
        if resp.text.strip() == "Ok.":
            return True
        logger.warning("qBittorrent login rejected: %s", resp.text.strip())
        return False
    except Exception as exc:  # noqa: BLE001
        logger.warning("qBittorrent login failed: %s", exc)
        return False


def _to_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_torrent(t: dict[str, Any]) -> dict[str, Any]:
    """Project a raw qBittorrent torrent dict into our normalized shape."""
    return {
        "hash": t.get("hash"),
        "name": t.get("name"),
        "state": t.get("state"),
        "num_seeds": _to_int(t.get("num_seeds")),
        "num_leechs": _to_int(t.get("num_leechs")),
        "seeds": _to_int(t.get("num_complete")),
        "peers": _to_int(t.get("num_incomplete")),
        "dlspeed": _to_int(t.get("dlspeed")),
        "progress": t.get("progress"),
    }


def fetch_torrents_raw(
    config: Config,
) -> tuple[bool, str | None, list[dict[str, Any]]]:
    """Read-only fetch of the qBittorrent torrent list. Returns (ok, error,
    torrents). Logs in with its own short-lived session."""
    if not config.service_enabled(SOURCE):
        return False, "service disabled or not configured", []

    svc = config.service(SOURCE)
    base_url = str(svc.get("base_url", "")).rstrip("/")
    username = svc.get("username", "")
    password = svc.get("password", "")
    torrents_endpoint = svc.get("torrents_endpoint", "/api/v2/torrents/info")

    try:
        with httpx.Client(timeout=15.0) as client:
            if not _login(client, base_url, username, password):
                return False, "login failed", []
            resp = client.get(f"{base_url}{torrents_endpoint}")
            resp.raise_for_status()
            torrents = resp.json()
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}", []

    if not isinstance(torrents, list):
        return False, "unexpected torrents payload shape (expected a list)", []
    return True, None, [t for t in torrents if isinstance(t, dict)]


def collect(config: Config) -> int:
    """Poll qBittorrent torrents. Returns the number of events stored."""
    if not config.service_enabled(SOURCE):
        logger.debug("qBittorrent collector disabled or not configured")
        return 0

    svc = config.service(SOURCE)
    base_url = str(svc.get("base_url", "")).rstrip("/")
    username = svc.get("username", "")
    password = svc.get("password", "")
    torrents_endpoint = svc.get("torrents_endpoint", "/api/v2/torrents/info")
    trackers_endpoint = svc.get("trackers_endpoint", "/api/v2/torrents/trackers")

    stored = 0
    try:
        with httpx.Client(timeout=15.0) as client:
            if not _login(client, base_url, username, password):
                return 0

            resp = client.get(f"{base_url}{torrents_endpoint}")
            resp.raise_for_status()
            torrents = resp.json()
            if not isinstance(torrents, list):
                logger.warning("Unexpected qBittorrent torrents payload shape")
                return 0

            for t in torrents:
                if not isinstance(t, dict):
                    continue
                try:
                    torrent_hash = t.get("hash")
                    payload = _normalize_torrent(t)

                    # Optional: fetch trackers for richer diagnosis context.
                    if torrent_hash and trackers_endpoint:
                        try:
                            tr = client.get(
                                f"{base_url}{trackers_endpoint}",
                                params={"hash": torrent_hash},
                            )
                            if tr.status_code == 200:
                                payload["trackers"] = tr.json()
                        except Exception as exc:  # noqa: BLE001
                            logger.debug(
                                "Tracker fetch failed for %s: %s",
                                torrent_hash,
                                exc,
                            )

                    db.insert_raw_event(
                        source=SOURCE,
                        event_type="torrent",
                        external_id=torrent_hash,
                        title=t.get("name"),
                        torrent_hash=str(torrent_hash).lower()
                        if torrent_hash
                        else None,
                        download_id=None,
                        payload=payload,
                        observed_at=None,
                    )
                    stored += 1
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Skipping malformed qBittorrent torrent: %s", exc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("qBittorrent poll failed: %s", exc)
        return stored

    logger.info("qBittorrent collector stored %d events", stored)
    return stored


def inspect(config: Config) -> dict[str, Any]:
    """Debug view: raw torrents, normalized records, per-torrent diagnostics and
    missing-field warnings for the current qBittorrent torrent list."""
    svc = config.service(SOURCE)
    ok, error, torrents = fetch_torrents_raw(config)

    normalized: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    warnings: list[str] = []

    for t in torrents:
        norm = _normalize_torrent(t)
        normalized.append(norm)
        diagnostics.append(
            {
                "hash": norm["hash"],
                "state": norm["state"],
                "classification": states.classify(norm["state"]),
                "is_active_download": states.is_active_download_state(norm["state"]),
                "is_seeding": states.is_seeding_state(norm["state"]),
                "available_keys": sorted(t.keys()),
            }
        )

        label = norm["name"] or norm["hash"]
        if not norm["state"]:
            warnings.append(f"torrent {label}: missing 'state' field")
        elif states.classify(norm["state"]) == states.OTHER:
            warnings.append(
                f"torrent {label}: unrecognized state '{norm['state']}' "
                "(classified as 'other')"
            )
        if norm["seeds"] is None and "num_complete" not in t:
            warnings.append(f"torrent {label}: missing 'num_complete' (seeds)")
        if norm["peers"] is None and "num_incomplete" not in t:
            warnings.append(f"torrent {label}: missing 'num_incomplete' (peers)")

    return {
        "service": SOURCE,
        "enabled": config.service_enabled(SOURCE),
        "url": f"{str(svc.get('base_url', '')).rstrip('/')}"
        f"{svc.get('torrents_endpoint', '/api/v2/torrents/info')}",
        "ok": ok,
        "error": error,
        "torrent_count": len(torrents),
        "raw": torrents,
        "normalized": normalized,
        "diagnostics": diagnostics,
        "warnings": warnings,
    }


def states_report(config: Config) -> dict[str, Any]:
    """Debug view: every unique qBittorrent state currently observed, counts per
    state, and how each state maps to the coarse diagnosis categories."""
    ok, error, torrents = fetch_torrents_raw(config)

    state_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    by_classification: dict[str, dict[str, Any]] = {
        cat: {"states": set(), "torrents": 0} for cat in states.CATEGORIES
    }

    for t in torrents:
        state = t.get("state") or "unknown"
        category = states.classify(state)
        state_counts[state] += 1
        category_counts[category] += 1
        bucket = by_classification[category]
        bucket["states"].add(state)
        bucket["torrents"] += 1

    classification = {
        cat: {
            "states": sorted(info["states"]),
            "torrents": info["torrents"],
        }
        for cat, info in by_classification.items()
    }

    return {
        "service": SOURCE,
        "enabled": config.service_enabled(SOURCE),
        "ok": ok,
        "error": error,
        "torrent_count": len(torrents),
        "unique_states": sorted(state_counts.keys()),
        "counts_per_state": dict(state_counts.most_common()),
        "classification": classification,
        "classification_counts": dict(category_counts.most_common()),
    }
