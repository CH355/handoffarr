"""qBittorrent collector.

Logs in via the Web API, maintains a cookie session, and polls the current
torrent list (read-only). Optionally fetches per-torrent trackers. Nothing is
added, removed, paused, resumed, or otherwise modified.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .. import db
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
                    payload = {
                        "hash": torrent_hash,
                        "name": t.get("name"),
                        "state": t.get("state"),
                        "num_seeds": _to_int(t.get("num_seeds")),
                        "num_leechs": _to_int(t.get("num_leechs")),
                        "seeds": _to_int(t.get("num_complete")),
                        "peers": _to_int(t.get("num_incomplete")),
                        "dlspeed": _to_int(t.get("dlspeed")),
                        "progress": t.get("progress"),
                    }

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
