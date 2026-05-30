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

from . import db, states
from .config import Config

logger = logging.getLogger("handoffarr.correlation")

_WORD_RE = re.compile(r"[a-z0-9]+")

# Confidence assigned to each correlation match source. Higher is more reliable.
CONFIDENCE_TORRENT_HASH = 1.0
CONFIDENCE_DOWNLOAD_ID = 0.8
CONFIDENCE_TITLE = 0.5
CONFIDENCE_NONE = 0.0


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

    # Completed / seeding torrents (uploading, stalledUP, stoppedUP, pausedUP,
    # ...) have already finished downloading. Swarm-failure, dead-swarm and
    # queue/disk-choking diagnoses are meaningless here, so short-circuit before
    # any of that logic can fire.
    if states.is_seeding_state(state):
        return "Completed / seeding state"

    # Everything below is swarm/download health and only applies while the
    # torrent is actively trying to download.
    active = states.is_active_download_state(state)

    if (
        active
        and reported_seeds is not None
        and reported_seeds >= healthy
        and actual_peers == 0
        and "stall" in state
    ):
        return (
            "Possible stale indexer/tracker metadata or qBittorrent "
            "connectivity issue"
        )

    if (
        active
        and reported_seeds is not None
        and reported_seeds <= low
        and actual_peers == 0
    ):
        return "Likely bad low-availability release selected upstream"

    if active and network_wide_zero_peers and actual_peers == 0:
        return "Possible qBittorrent/VPN/network issue"

    if active and actual_peers is not None and actual_peers > 0 and dlspeed == 0:
        return "Possible queue, disk, or peer choking issue"

    return "Healthy / no issue detected"


def build_traces(config: Config) -> list[dict[str, Any]]:
    """Rebuild handoff traces from recent events.

    Each trace carries both the dashboard-facing columns and extra correlation
    diagnostics (``match_source``, ``match_confidence``, ``match_reasons``,
    ``normalized_title``). The DB layer only persists the known columns, so the
    diagnostics are free for the debug endpoints to consume in-memory.
    """
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

    # Network-wide stall heuristic across actively-downloading torrents only.
    # Completed / seeding torrents legitimately show zero download peers, so
    # including them here would falsely trip the "VPN/network" diagnosis.
    active = [
        e
        for e in qbit_by_hash.values()
        if states.is_active_download_state(_parse_payload(e).get("state"))
    ]
    zero_peer_active = 0
    for ev in active:
        p = _parse_payload(ev)
        peers = p.get("peers")
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
        match_source: str | None = None
        match_confidence = CONFIDENCE_NONE
        match_reasons: list[str] = []

        if matching.get("prefer_torrent_hash", True) and torrent_hash:
            cand = qbit_by_hash.get(torrent_hash)
            if cand is not None:
                q_ev = cand
                match_source = "torrent_hash"
                match_confidence = CONFIDENCE_TORRENT_HASH
                match_reasons.append(
                    f"Radarr torrent hash {torrent_hash[:12]}… matched a "
                    "qBittorrent torrent hash exactly"
                )
        if q_ev is None and matching.get("fallback_to_download_id", True) and download_id:
            for cand in qbit_by_hash.values():
                if (cand.get("torrent_hash") or "") == str(download_id).lower():
                    q_ev = cand
                    match_source = "download_id"
                    match_confidence = CONFIDENCE_DOWNLOAD_ID
                    match_reasons.append(
                        f"Radarr download id {download_id} matched a "
                        "qBittorrent torrent hash"
                    )
                    break
        if (
            q_ev is None
            and matching.get("fallback_to_normalized_title", True)
            and norm_title
        ):
            cand = qbit_by_norm_title.get(norm_title)
            if cand is not None:
                q_ev = cand
                match_source = "title_match"
                match_confidence = CONFIDENCE_TITLE
                match_reasons.append(
                    f"normalized title '{norm_title}' matched a qBittorrent "
                    "torrent name"
                )
        if q_ev is None:
            match_reasons.append("no qBittorrent torrent matched")

        q_payload = _parse_payload(q_ev) if q_ev else {}

        # --- Match Seerr request by normalized title within time window ---
        seerr_id = None
        seerr_status = None
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
                seerr_status = s_payload.get("status")
                break
        if seerr_id:
            used_seerr_ids.add(seerr_id)
            match_reasons.append(
                f"normalized title matched Seerr request {seerr_id} within the "
                f"{title_window}m window"
            )

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
                "normalized_title": norm_title,
                "seerr_request_id": seerr_id,
                "seerr_status": seerr_status,
                "radarr_history_id": radarr_id,
                "torrent_hash": q_ev.get("torrent_hash") if q_ev else torrent_hash,
                "download_id": download_id,
                "selected_release": r_payload.get("sourceTitle"),
                "reported_seeds": r_payload.get("reported_seeds"),
                "reported_indexer": r_payload.get("indexer"),
                "qbittorrent_state": q_payload.get("state"),
                "state_classification": states.classify(q_payload.get("state")),
                "actual_seeds": q_payload.get("seeds"),
                "actual_peers": q_payload.get("peers"),
                "dlspeed": q_payload.get("dlspeed"),
                "match_source": match_source,
                "match_confidence": match_confidence,
                "match_reasons": match_reasons,
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
                "normalized_title": _normalize_title(
                    s_payload.get("title") or s_ev.get("title")
                ),
                "seerr_request_id": s_id,
                "seerr_status": s_payload.get("status"),
                "radarr_history_id": None,
                "torrent_hash": None,
                "download_id": None,
                "selected_release": None,
                "reported_seeds": None,
                "reported_indexer": None,
                "qbittorrent_state": None,
                "state_classification": None,
                "actual_seeds": None,
                "actual_peers": None,
                "dlspeed": None,
                "match_source": None,
                "match_confidence": CONFIDENCE_NONE,
                "match_reasons": ["Seerr request with no matching Radarr grab"],
                "diagnosis": "Request not yet handed to Radarr or correlation failed",
            }
        )

    return traces


def run_correlation(config: Config) -> int:
    """Rebuild and persist handoff traces. Returns the trace count."""
    traces = build_traces(config)
    db.replace_traces(traces)
    logger.info("Correlation produced %d traces", len(traces))
    return len(traces)


def correlation_report(config: Config) -> list[dict[str, Any]]:
    """Correlation diagnostics for the debug endpoint.

    Returns, per trace, why it matched (``match_reasons``), the ``match_source``
    (torrent_hash / download_id / title_match / none) and a ``confidence`` score,
    without touching the database.
    """
    report: list[dict[str, Any]] = []
    for t in build_traces(config):
        report.append(
            {
                "title": t.get("title"),
                "normalized_title": t.get("normalized_title"),
                "seerr_request_id": t.get("seerr_request_id"),
                "radarr_history_id": t.get("radarr_history_id"),
                "torrent_hash": t.get("torrent_hash"),
                "download_id": t.get("download_id"),
                "match_source": t.get("match_source"),
                "confidence": t.get("match_confidence"),
                "match_reasons": t.get("match_reasons"),
                "qbittorrent_state": t.get("qbittorrent_state"),
                "state_classification": t.get("state_classification"),
                "diagnosis": t.get("diagnosis"),
            }
        )
    return report
