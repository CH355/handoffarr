"""Current qBittorrent snapshot projections used by the product UI."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

DEAD_RECOMMENDATION = "Remove and search for another release."


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def torrent_response(
    torrents: list[dict[str, Any]], *, now: datetime | None = None
) -> dict[str, Any]:
    current_time = now or datetime.now(timezone.utc)
    today = current_time.astimezone(timezone.utc).date()
    dead = [torrent for torrent in torrents if torrent.get("dead_torrent") is True]
    dead_size = sum(
        _to_int(torrent.get("total_size") or torrent.get("size")) for torrent in dead
    )
    # Count newly detected current failures, not every repeat poll today.
    dead_today = sum(
        1
        for torrent in dead
        if torrent.get("dead_since")
        and datetime.fromisoformat(
            str(torrent["dead_since"]).replace("Z", "+00:00")
        ).astimezone(timezone.utc).date() == today
    )
    summary = {
        "dead_torrents": len(dead),
        "dead_torrents_size": dead_size,
        "dead_torrents_today": dead_today,
    }
    return {
        "summary": summary,
        **summary,
        "health": {
            "name": "Dead Torrents",
            "count": len(dead),
            "message": f"{len(dead)} dead torrents detected",
            "description": (
                "These torrents have 0% availability and cannot currently "
                "download because no seeders are available."
            ),
            "severity": (
                "critical" if len(dead) > 25 else "warning" if dead else "healthy"
            ),
        },
        "torrents": torrents,
    }


def torrent_detail(
    torrent_hash: str, torrents: list[dict[str, Any]]
) -> dict[str, Any] | None:
    target = torrent_hash.strip().lower()
    for torrent in torrents:
        if str(torrent.get("hash") or "").lower() != target:
            continue
        return {
            **torrent,
            "availability_percent": max(
                0.0, float(torrent.get("availability") or 0) * 100
            ),
            "seeders": _to_int(torrent.get("num_seeds")),
            "peers": _to_int(torrent.get("num_leechs")),
            "health": "Dead torrent" if torrent.get("dead_torrent") else "Available",
            "recommendation": (
                DEAD_RECOMMENDATION if torrent.get("dead_torrent") else None
            ),
        }
    return None
