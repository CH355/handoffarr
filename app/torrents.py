"""Recovery projections derived from the current qBittorrent snapshot."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _to_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _availability_percent(torrent: dict[str, Any]) -> float | None:
    availability = _to_float(torrent.get("availability"))
    return min(100.0, availability * 100) if availability is not None else None


def _status(torrent: dict[str, Any]) -> str:
    if torrent.get("dead_torrent") is True:
        return "dead"
    state = str(torrent.get("state") or "").lower()
    if state in {"stalleddl", "stalledup"}:
        return "stalled"
    if state in {"queueddl", "queuedup"}:
        return "queued"
    if state in {
        "downloading",
        "forceddl",
        "metadl",
        "checkingdl",
        "allocating",
    }:
        return "downloading"
    return "healthy"


def _media_type(torrent: dict[str, Any]) -> str:
    explicit = str(torrent.get("media_type") or "").strip()
    if explicit:
        return explicit
    source = " ".join(
        str(torrent.get(key) or "") for key in ("category", "tags")
    ).lower()
    if "sonarr" in source or "series" in source or "tv" in source:
        return "Series"
    if "radarr" in source or "movie" in source:
        return "Movie"
    return "Unknown"


def recommendation_for(torrent: dict[str, Any]) -> tuple[str | None, str]:
    """Return the rule-based recovery recommendation and its evidence."""
    status = _status(torrent)
    availability = _availability_percent(torrent)
    seeders = _to_int(torrent.get("num_seeds"))

    if status == "dead":
        return (
            "Recover",
            str(torrent.get("dead_reason") or "No available seeders or pieces."),
        )
    if status == "healthy":
        return None, "The torrent is complete or reporting a healthy state."
    if availability is not None and availability < 5:
        return (
            "Replace soon",
            f"Availability is {availability:.1f}%, below the 5% threshold.",
        )
    if seeders < 3:
        return "Monitor", f"Only {seeders} seeders are currently available."
    return None, "Availability and seeder counts are currently sufficient."


def enrich_torrent(
    torrent: dict[str, Any],
    evaluation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    recommendation, reason = recommendation_for(torrent)
    name = str(torrent.get("name") or torrent.get("hash") or "Unknown release")
    recommended = (evaluation or {}).get("recommended_candidate")
    media_type = _media_type(torrent)
    if media_type == "Unknown":
        media_type = {
            "radarr": "Movie",
            "sonarr": "Episode",
        }.get(str((evaluation or {}).get("provider") or ""), media_type)
    return {
        **torrent,
        "media_title": (
            (evaluation or {}).get("media_title")
            or torrent.get("media_title")
            or name
        ),
        "media_type": media_type,
        "current_release": name,
        "availability_percent": _availability_percent(torrent),
        "seeders": _to_int(torrent.get("num_seeds")),
        "peers": _to_int(torrent.get("num_leechs")),
        "recovery_status": _status(torrent),
        "recommendation": recommendation,
        "recommendation_reason": reason,
        "replacement_candidates": (evaluation or {}).get("candidates") or [],
        "best_replacement": (
            recommended.get("release_name")
            if isinstance(recommended, dict)
            else None
        ),
        "replacement_health_score": (
            recommended.get("score") if isinstance(recommended, dict) else None
        ),
        "replacement_recommendation": (evaluation or {}).get(
            "recommendation_explanation"
        ),
        "replacement_recommendation_reasons": (evaluation or {}).get(
            "recommendation_reasons"
        )
        or [],
        "alternatives_evaluated_at": (evaluation or {}).get("evaluated_at"),
    }


def torrent_response(
    torrents: list[dict[str, Any]],
    *,
    now: datetime | None = None,
    evaluations: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    current_time = now or datetime.now(timezone.utc)
    today = current_time.astimezone(timezone.utc).date()
    enriched = [
        enrich_torrent(
            torrent,
            (evaluations or {}).get(str(torrent.get("hash") or "").lower()),
        )
        for torrent in torrents
    ]
    dead = [torrent for torrent in enriched if torrent["recovery_status"] == "dead"]
    stalled = [
        torrent for torrent in enriched if torrent["recovery_status"] == "stalled"
    ]
    healthy = [
        torrent for torrent in enriched if torrent["recovery_status"] == "healthy"
    ]
    dead_size = sum(
        _to_int(torrent.get("total_size") or torrent.get("size")) for torrent in dead
    )
    dead_today = sum(
        1
        for torrent in dead
        if torrent.get("dead_since")
        and datetime.fromisoformat(
            str(torrent["dead_since"]).replace("Z", "+00:00")
        )
        .astimezone(timezone.utc)
        .date()
        == today
    )
    summary = {
        "total_torrents": len(enriched),
        "dead_torrents": len(dead),
        "stalled_torrents": len(stalled),
        "downloading_torrents": sum(
            torrent["recovery_status"] == "downloading" for torrent in enriched
        ),
        "queued_torrents": sum(
            torrent["recovery_status"] == "queued" for torrent in enriched
        ),
        "healthy_torrents": len(healthy),
        "potentially_recoverable": len(dead) + len(stalled),
        "dead_torrents_size": dead_size,
        "dead_torrents_today": dead_today,
    }
    return {
        "summary": summary,
        **summary,
        "health": {
            "name": "Recovery Center",
            "count": len(dead),
            "message": f"{len(dead)} torrents need recovery",
            "description": (
                f"{len(stalled)} additional torrents are stalled. Review the "
                "current qBittorrent snapshot in the Recovery Center."
            ),
            "severity": (
                "critical" if len(dead) > 25 else "warning" if dead else "healthy"
            ),
        },
        "torrents": enriched,
    }


def torrent_detail(
    torrent_hash: str,
    torrents: list[dict[str, Any]],
    *,
    evaluation: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    target = torrent_hash.strip().lower()
    for torrent in torrents:
        if str(torrent.get("hash") or "").lower() == target:
            return enrich_torrent(torrent, evaluation)
    return None
