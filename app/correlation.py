"""Correlate the Seerr -> Radarr -> qBittorrent handoff.

Builds one passthrough trace per known media item by stitching together the most
recent raw events from each collector, then applies the diagnosis rules. This is
intentionally simple: traces are rebuilt from scratch on each pass.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from . import db
from .config import Config

logger = logging.getLogger("handoffarr.correlation")

_WORD_RE = re.compile(r"[a-z0-9]+")


def _normalize_title(title: str | None) -> str:
    if not title:
        return ""
    # Lowercase, strip release noise, keep alphanumeric word stems.
    words = _WORD_RE.findall(title.lower())
    # Drop very common quality/source tokens that hurt matching.
    noise = {
        "1080p", "720p", "2160p", "4k", "x264", "x265", "h264", "h265",
        "hevc", "web", "webrip", "webdl", "bluray", "bdrip", "hdrip",
        "proper", "repack", "remux", "amzn", "nf", "dts", "aac", "ddp",
    }
    return " ".join(w for w in words if w not in noise)


def _parse_payload(event: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(event.get("payload_json") or "{}")
    except Exception:  # noqa: BLE001
        return {}


def _latest_by(events: list[dict[str, Any]], key_fn) -> dict[str, dict[str, Any]]:
    """Keep the most recent event per key (events arrive newest-first)."""
    out: dict[str, dict[str, Any]] = {}
    for ev in events:
        key = key_fn(ev)
        if key is None or key == "":
            continue
        if key not in out:  # first seen == newest
            out[key] = ev
    return out


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:  # noqa: BLE001
        return None


def diagnose(
    *,
    thresholds: dict[str, Any],
    reported_seeds: int | None,
    actual_peers: int | None,
    actual_seeds: int | None,
    qb_state: str | None,
    dlspeed: int | None,
    has_radarr: bool,
    has_qbittorrent: bool,
    network_wide_zero_peers: bool,
) -> str:
    low = thresholds.get("low_reported_seeds", 5)
    healthy = thresholds.get("healthy_reported_seeds", 20)
    state = (qb_state or "").lower()

    if not has_radarr:
        return "Request not yet handed to Radarr or correlation failed"
    if has_radarr and not has_qbittorrent:
        return "Radarr selected a release but qBittorrent did not receive or expose it"

    if (
        reported_seeds is not None
        and reported_seeds >= healthy
        and actual_peers == 0
        and "stall" in state
    ):
        return (
            "Possible stale indexer/tracker metadata or qBittorrent "
            "connectivity issue"
        )

    if reported_seeds is not None and reported_seeds <= low and actual_peers == 0:
        return "Likely bad low-availability release selected upstream"

    if network_wide_zero_peers and actual_peers == 0:
        return "Possible qBittorrent/VPN/network issue"

    if actual_peers is not None and actual_peers > 0 and dlspeed == 0:
        return "Possible queue, disk, or peer choking issue"

    return "Healthy / no issue detected"


def run_correlation(config: Config) -> int:
    """Rebuild handoff traces from recent events. Returns trace count."""
    lookback_minutes = int(config.app.get("lookback_minutes", 120))
    since = (
        datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
    ).isoformat()

    matching = config.matching
    thresholds = config.thresholds
    title_window = int(matching.get("title_time_window_minutes", 60))

    seerr_events = db.events_for_source_since("seerr", since)
    radarr_events = db.events_for_source_since("radarr", since)
    qbit_events = db.events_for_source_since("qbittorrent", since)

    # Latest snapshot per entity.
    seerr_by_id = _latest_by(seerr_events, lambda e: e.get("external_id"))
    radarr_by_id = _latest_by(radarr_events, lambda e: e.get("external_id"))
    qbit_by_hash = _latest_by(qbit_events, lambda e: e.get("torrent_hash"))

    # Secondary qBittorrent indexes for fallback matching.
    qbit_by_norm_title: dict[str, dict[str, Any]] = {}
    for ev in qbit_by_hash.values():
        norm = _normalize_title(ev.get("title"))
        if norm and norm not in qbit_by_norm_title:
            qbit_by_norm_title[norm] = ev

    # Network-wide stall heuristic across active torrents.
    active = [e for e in qbit_by_hash.values()]
    zero_peer_active = 0
    for ev in active:
        p = _parse_payload(ev)
        state = str(p.get("state", "")).lower()
        peers = p.get("peers")
        if state in {"downloading", "stalleddl", "metadl", "stalledup"}:
            if (peers or 0) == 0:
                zero_peer_active += 1
    network_wide_zero_peers = len(active) >= 3 and zero_peer_active >= max(
        2, len(active) // 2
    )

    used_seerr_ids: set[str] = set()
    traces: list[dict[str, Any]] = []

    for radarr_id, r_ev in radarr_by_id.items():
        r_payload = _parse_payload(r_ev)
        torrent_hash = (r_ev.get("torrent_hash") or "").lower() or None
        download_id = r_ev.get("download_id")
        title = r_ev.get("title") or r_payload.get("sourceTitle")
        norm_title = _normalize_title(title)

        # --- Match qBittorrent torrent ---
        q_ev = None
        if matching.get("prefer_torrent_hash", True) and torrent_hash:
            q_ev = qbit_by_hash.get(torrent_hash)
        if q_ev is None and matching.get("fallback_to_download_id", True) and download_id:
            for cand in qbit_by_hash.values():
                if (cand.get("torrent_hash") or "") == str(download_id).lower():
                    q_ev = cand
                    break
        if (
            q_ev is None
            and matching.get("fallback_to_normalized_title", True)
            and norm_title
        ):
            q_ev = qbit_by_norm_title.get(norm_title)

        q_payload = _parse_payload(q_ev) if q_ev else {}

        # --- Match Seerr request by normalized title within time window ---
        seerr_id = None
        r_time = _parse_time(r_ev.get("observed_at"))
        for s_id, s_ev in seerr_by_id.items():
            s_payload = _parse_payload(s_ev)
            if _normalize_title(s_payload.get("title")) == norm_title and norm_title:
                if r_time is not None:
                    s_time = _parse_time(
                        s_payload.get("requested_at")
                    ) or _parse_time(s_ev.get("observed_at"))
                    if s_time is not None and abs(
                        (r_time - s_time).total_seconds()
                    ) > title_window * 60:
                        continue
                seerr_id = s_id
                break
        if seerr_id:
            used_seerr_ids.add(seerr_id)

        diagnosis = diagnose(
            thresholds=thresholds,
            reported_seeds=r_payload.get("reported_seeds"),
            actual_peers=q_payload.get("peers"),
            actual_seeds=q_payload.get("seeds"),
            qb_state=q_payload.get("state"),
            dlspeed=q_payload.get("dlspeed"),
            has_radarr=True,
            has_qbittorrent=q_ev is not None,
            network_wide_zero_peers=network_wide_zero_peers,
        )

        traces.append(
            {
                "title": title,
                "seerr_request_id": seerr_id,
                "radarr_history_id": radarr_id,
                "torrent_hash": q_ev.get("torrent_hash") if q_ev else torrent_hash,
                "download_id": download_id,
                "selected_release": r_payload.get("sourceTitle"),
                "reported_seeds": r_payload.get("reported_seeds"),
                "reported_indexer": r_payload.get("indexer"),
                "qbittorrent_state": q_payload.get("state"),
                "actual_seeds": q_payload.get("seeds"),
                "actual_peers": q_payload.get("peers"),
                "diagnosis": diagnosis,
            }
        )

    # Seerr requests with no Radarr match.
    for s_id, s_ev in seerr_by_id.items():
        if s_id in used_seerr_ids:
            continue
        s_payload = _parse_payload(s_ev)
        traces.append(
            {
                "title": s_payload.get("title") or s_ev.get("title"),
                "seerr_request_id": s_id,
                "radarr_history_id": None,
                "torrent_hash": None,
                "download_id": None,
                "selected_release": None,
                "reported_seeds": None,
                "reported_indexer": None,
                "qbittorrent_state": None,
                "actual_seeds": None,
                "actual_peers": None,
                "diagnosis": "Request not yet handed to Radarr or correlation failed",
            }
        )

    db.replace_traces(traces)
    logger.info("Correlation produced %d traces", len(traces))
    return len(traces)
