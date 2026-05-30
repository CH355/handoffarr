"""Decision evidence collector.

Builds read-only DecisionObservation records from already-persisted raw events
(Seerr requests, Radarr/Sonarr/Lidarr history, qBittorrent torrents, import
events). The collector itself fetches nothing new; it projects the data already
captured by other collectors into one row per selected release so the decision
interpreter can answer "why was this torrent selected, and was the selection
reasonable?"

This collector never mutates Seerr, Radarr/Sonarr/Lidarr, or qBittorrent.
Candidate evidence here means *every grab Handoffarr has observed for the same
normalized media title*. Handoffarr does not see rejected indexer search
results, so the candidate set is the observable history of alternative
selections, not the indexer's full pick list.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from .. import db
from ..config import Config

logger = logging.getLogger("handoffarr.collectors.decision")

SOURCE = "decision"
_WORD_RE = re.compile(r"[a-z0-9]+")

# Radarr / Sonarr / Lidarr history event types that represent a release being
# selected and grabbed for download. Mirrors the Radarr collector's GRAB_EVENT_TYPES
# but kept local so the decision collector can be reasoned about in isolation.
GRAB_EVENT_TYPES = {"grabbed"}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_payload(event: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(event.get("payload_json") or "{}")
    except Exception:  # noqa: BLE001
        return {}


def _normalize_title(title: str | None) -> str:
    if not title:
        return ""
    noise = {
        "1080p", "720p", "2160p", "4k", "x264", "x265", "h264", "h265",
        "hevc", "web", "webrip", "webdl", "bluray", "bdrip", "hdrip",
        "proper", "repack", "remux", "amzn", "nf", "dts", "aac", "ddp",
        "season", "episode",
    }
    return " ".join(w for w in _WORD_RE.findall(title.lower()) if w not in noise)


def _latest_by(events: list[dict[str, Any]], key_fn) -> dict[str, dict[str, Any]]:
    """Keep the most recent event per key (events arrive newest-first)."""
    out: dict[str, dict[str, Any]] = {}
    for event in events:
        key = key_fn(event)
        if key is None or key == "":
            continue
        key = str(key)
        if key not in out:
            out[key] = event
    return out


def _to_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _stable_decision_id(media_id: str, torrent_hash: str | None, history_id: str | None) -> str:
    parts = [p for p in (media_id, torrent_hash, history_id) if p]
    return "decision:" + ":".join(parts) if parts else "decision:unknown"


def _seerr_index(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Index latest Seerr request by normalized title."""
    by_norm: dict[str, dict[str, Any]] = {}
    for event in events:
        payload = _parse_payload(event)
        norm = _normalize_title(payload.get("title") or event.get("title"))
        if norm and norm not in by_norm:
            by_norm[norm] = {
                "request_id": event.get("external_id"),
                "status": payload.get("status"),
                "title": payload.get("title") or event.get("title"),
            }
    return by_norm


def _qbit_by_hash(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return _latest_by(events, lambda e: (e.get("torrent_hash") or "").lower() or None)


def _build_observations(config: Config, observed_at: str) -> list[dict[str, Any]]:
    lookback_minutes = int(config.app.get("lookback_minutes", 120))
    since = (
        datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
    ).isoformat()

    seerr_events = db.events_for_source_since("seerr", since)
    radarr_events = [
        e
        for e in db.events_for_source_since("radarr", since)
        if not str(e.get("event_type") or "").startswith("import_")
    ]
    qbit_events = db.events_for_source_since("qbittorrent", since)

    seerr_by_norm = _seerr_index(seerr_events)
    qbit_by_hash = _qbit_by_hash(qbit_events)

    # Group every observed grab by normalized title so we can count siblings
    # as candidate evidence (alternative releases Handoffarr saw for the same
    # title). Newest grab per (history_id) wins as the "selected" release.
    grabs_by_norm: dict[str, list[dict[str, Any]]] = {}
    for event in radarr_events:
        payload = _parse_payload(event)
        norm = _normalize_title(
            payload.get("movie_title")
            or event.get("title")
            or payload.get("sourceTitle")
        )
        if not norm:
            continue
        grabs_by_norm.setdefault(norm, []).append(event)

    # All imports across radarr/sonarr/lidarr give us the source_application
    # attribution. Key the lookup by torrent hash (most reliable) then norm
    # title (fallback) so we can attribute the selection to the right app.
    imports_by_hash: dict[str, dict[str, Any]] = {}
    imports_by_norm: dict[str, dict[str, Any]] = {}
    for import_event in db.all_import_events():
        evidence = import_event.get("evidence") or {}
        torrent_hash = str(evidence.get("torrent_hash") or "").lower()
        norm = _normalize_title(import_event.get("media_title"))
        if torrent_hash and torrent_hash not in imports_by_hash:
            imports_by_hash[torrent_hash] = import_event
        if norm and norm not in imports_by_norm:
            imports_by_norm[norm] = import_event

    observations: list[dict[str, Any]] = []
    seen_decision_ids: set[str] = set()

    for norm, grabs in grabs_by_norm.items():
        # Newest grab per group is the current selection; older grabs are
        # candidate evidence of prior alternatives for the same title.
        selected = grabs[0]
        selected_payload = _parse_payload(selected)
        torrent_hash = (selected.get("torrent_hash") or "").lower() or None
        history_id = selected.get("external_id")

        # Source application: prefer the import event's source app (the actual
        # downstream importer); fall back to "radarr" since we got the grab
        # from radarr history.
        import_event = None
        if torrent_hash and torrent_hash in imports_by_hash:
            import_event = imports_by_hash[torrent_hash]
        elif norm in imports_by_norm:
            import_event = imports_by_norm[norm]
        source_application = (
            import_event.get("source_application") if import_event else "radarr"
        )

        media_id_value = (
            str(import_event.get("media_id")) if import_event and import_event.get("media_id") else None
        )
        media_id = media_id_value or norm or (torrent_hash or history_id or "unknown")

        seerr_match = seerr_by_norm.get(norm)
        qbit_event = qbit_by_hash.get(torrent_hash) if torrent_hash else None
        qbit_payload = _parse_payload(qbit_event) if qbit_event else {}

        candidate_count = len(grabs)
        candidates: list[dict[str, Any]] = []
        for grab in grabs:
            grab_payload = _parse_payload(grab)
            candidates.append(
                {
                    "history_id": grab.get("external_id"),
                    "release": grab_payload.get("sourceTitle"),
                    "indexer": grab_payload.get("indexer"),
                    "reported_seeds": grab_payload.get("reported_seeds"),
                    "torrent_hash": (grab.get("torrent_hash") or "").lower() or None,
                    "observed_at": grab.get("observed_at"),
                    "is_selected": grab.get("external_id") == history_id,
                }
            )

        decision_id = _stable_decision_id(media_id, torrent_hash, str(history_id) if history_id else None)
        if decision_id in seen_decision_ids:
            continue
        seen_decision_ids.add(decision_id)

        observation = {
            "decision_id": decision_id,
            "media_id": media_id,
            "media_title": selected.get("title") or selected_payload.get("movie_title"),
            "selected_release": selected_payload.get("sourceTitle"),
            "source_application": source_application,
            "source_indexer": selected_payload.get("indexer"),
            "reported_seeds": _to_int(selected_payload.get("reported_seeds")),
            "download_id": selected.get("download_id"),
            "torrent_hash": torrent_hash,
            "radarr_history_id": history_id,
            "candidate_count": candidate_count,
            "candidates": candidates,
            "seerr_request_id": (seerr_match or {}).get("request_id"),
            "seerr_status": (seerr_match or {}).get("status"),
            "qbittorrent_state": qbit_payload.get("state"),
            "actual_peers": _to_int(qbit_payload.get("peers")),
            "actual_seeds": _to_int(qbit_payload.get("seeds")),
            "dlspeed": _to_int(qbit_payload.get("dlspeed")),
            "import_status": import_event.get("import_status") if import_event else None,
            "import_timestamp": (
                import_event.get("import_timestamp") if import_event else None
            ),
            "observed_at": observed_at,
        }
        observations.append(observation)

    return observations


def collect(config: Config) -> int:
    """Persist decision evidence observations via raw_events."""
    observed_at = _utcnow()
    stored = 0
    for observation in _build_observations(config, observed_at):
        db.insert_raw_event(
            source=SOURCE,
            event_type="observation",
            external_id=observation["decision_id"],
            title=observation.get("media_title"),
            torrent_hash=observation.get("torrent_hash"),
            download_id=observation.get("download_id"),
            payload=observation,
            observed_at=observed_at,
        )
        stored += 1
    logger.info("Decision collector stored %d observations", stored)
    return stored
