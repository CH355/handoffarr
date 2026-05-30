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

# Default qBittorrent Web API v2 endpoints. All overridable per-service in config.
TRANSFER_INFO_ENDPOINT = "/api/v2/transfer/info"
PREFERENCES_ENDPOINT = "/api/v2/app/preferences"
SPEED_LIMITS_MODE_ENDPOINT = "/api/v2/transfer/speedLimitsMode"
MAINDATA_ENDPOINT = "/api/v2/sync/maindata"
PROPERTIES_ENDPOINT = "/api/v2/torrents/properties"
PEERS_ENDPOINT = "/api/v2/sync/torrentPeers"

# Disk-space thresholds (bytes) for the free-space finding, when detectable.
DISK_CRITICAL_BYTES = 512 * 1024 * 1024  # 512 MiB
DISK_LOW_BYTES = 2 * 1024 * 1024 * 1024  # 2 GiB

# Heuristic thresholds for the queue diagnosis.
STALLED_MIN_COUNT = 2  # below this, stalled torrents are not noteworthy
METADATA_MIN_COUNT = 2  # below this, metadata fetches are normal churn

# qBittorrent tracker "status" enum -> human label.
TRACKER_STATUS = {
    0: "disabled",
    1: "not contacted",
    2: "working",
    3: "updating",
    4: "not working",
}


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
                    payload = _normalize_torrent_full(t)

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


# --- Queue diagnostics ----------------------------------------------------
# Read-only inspection of qBittorrent's transfer/queue/connection state to work
# out *why* downloads are not progressing. Nothing is ever modified.


def _safe_get(
    client: httpx.Client,
    base_url: str,
    endpoint: str,
    errors: dict[str, str],
    key: str,
    params: dict[str, Any] | None = None,
) -> Any:
    """GET an endpoint, returning parsed JSON (or text) or None on failure.

    Per-endpoint failures are recorded in ``errors`` rather than raised, so one
    missing endpoint (e.g. an older qBittorrent without ``sync/maindata``) does
    not sink the whole report."""
    try:
        resp = client.get(f"{base_url}{endpoint}", params=params)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        errors[key] = f"{type(exc).__name__}: {exc}"
        return None
    try:
        return resp.json()
    except Exception:  # noqa: BLE001 - speedLimitsMode returns a bare "0"/"1"
        return resp.text.strip()


def _as_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() not in ("", "0", "false", "False")
    return bool(value)


def _count_states(torrents: list[dict[str, Any]]) -> dict[str, Any]:
    """Bucket the torrent list into the queue-relevant counts."""
    per_state: Counter[str] = Counter()
    per_class: Counter[str] = Counter()
    for t in torrents:
        state = (t.get("state") or "unknown").lower()
        per_state[state] += 1
        per_class[states.classify(state)] += 1

    working = (
        per_state["downloading"]
        + per_state["forceddl"]
        + per_state["allocating"]
        + per_state["checkingdl"]
        + per_state["checkingresumedata"]
        + per_state["moving"]
    )
    metadata = per_state["metadl"]
    stalled = per_state["stalleddl"]
    queued = per_state["queueddl"]
    paused = per_state["pauseddl"] + per_state["stoppeddl"]
    active_uploads = per_state["uploading"] + per_state["forcedup"]
    errored = per_class[states.ERROR]
    completed = per_class[states.COMPLETED] + per_class[states.UPLOADING]

    # Torrents occupying a download slot in qBittorrent's queue accounting.
    slots_used = working + metadata + stalled

    return {
        "total": len(torrents),
        "active_downloads": working + metadata,
        "working_downloads": working,
        "metadata_downloads": metadata,
        "stalled_downloads": stalled,
        "queued_downloads": queued,
        "paused_downloads": paused,
        "active_uploads": active_uploads,
        "completed": completed,
        "errored": errored,
        "download_slots_used": slots_used,
        "by_state": dict(per_state.most_common()),
        "by_classification": dict(per_class.most_common()),
    }


def _finding(code: str, severity: str, title: str, detail: str) -> dict[str, str]:
    return {"code": code, "severity": severity, "title": title, "detail": detail}


def diagnose_queue(
    *,
    counts: dict[str, Any],
    prefs: dict[str, Any],
    transfer: dict[str, Any],
    server_state: dict[str, Any],
    alt_speed_on: bool | None,
) -> tuple[str, str, list[dict[str, str]]]:
    """Return (primary_label, severity, findings).

    ``primary_label`` is one of the six queue-health labels (or "Healthy
    queue"); ``findings`` explains every condition detected, even ones that did
    not win the primary slot."""
    findings: list[dict[str, str]] = []

    queueing_enabled = _as_bool(prefs.get("queueing_enabled"))
    max_active_dl = _to_int(prefs.get("max_active_downloads"))
    dont_count_slow = _as_bool(prefs.get("dont_count_slow_torrents"))

    working = counts["working_downloads"]
    metadata = counts["metadata_downloads"]
    stalled = counts["stalled_downloads"]
    queued = counts["queued_downloads"]
    paused = counts["paused_downloads"]
    errored = counts["errored"]
    slots_used = counts["download_slots_used"]
    active = counts["active_downloads"]

    connection_status = (
        transfer.get("connection_status")
        or server_state.get("connection_status")
        or ""
    ).lower()
    dht_nodes = _to_int(transfer.get("dht_nodes"))
    if dht_nodes is None:
        dht_nodes = _to_int(server_state.get("dht_nodes"))
    dl_speed = _to_int(transfer.get("dl_info_speed"))
    if dl_speed is None:
        dl_speed = _to_int(server_state.get("dl_info_speed"))

    free_space = _to_int(server_state.get("free_space_on_disk"))
    dl_limit = _to_int(transfer.get("dl_rate_limit"))
    if dl_limit is None:
        dl_limit = _to_int(server_state.get("dl_rate_limit"))

    slots_full = (
        bool(queueing_enabled)
        and max_active_dl is not None
        and max_active_dl > 0
        and slots_used >= max_active_dl
    )

    # --- Connection / network / VPN -----------------------------------
    network_issue = False
    if connection_status == "disconnected":
        network_issue = True
        findings.append(
            _finding(
                "connection_disconnected",
                "critical",
                "qBittorrent connection status is 'disconnected'",
                "qBittorrent reports no connection to the BitTorrent network. "
                "This usually means the listening port is unreachable or the "
                "VPN/network is down, so no torrent can find peers.",
            )
        )
    elif connection_status == "firewalled":
        findings.append(
            _finding(
                "connection_firewalled",
                "warning",
                "qBittorrent connection status is 'firewalled'",
                "Incoming connections are blocked (port not forwarded). "
                "Downloads can still work via outgoing connections but peer "
                "availability is reduced.",
            )
        )
    if dht_nodes == 0:
        findings.append(
            _finding(
                "dht_no_nodes",
                "warning",
                "DHT has 0 nodes",
                "The DHT network is unreachable. Combined with stalled torrents "
                "this strongly suggests a network/VPN/firewall problem.",
            )
        )
    # Widespread stall with peers nowhere to be found.
    if active >= 3 and stalled >= max(2, active // 2) and (dl_speed or 0) == 0:
        network_issue = True
        findings.append(
            _finding(
                "widespread_stall",
                "warning",
                "Most active downloads are stalled with zero throughput",
                f"{stalled} of {active} active downloads are stalled and global "
                "download speed is 0. When this is fleet-wide (not one bad "
                "torrent) the cause is typically the network, VPN, or qBittorrent "
                "connectivity rather than the individual releases.",
            )
        )

    # --- Disk space ---------------------------------------------------
    if free_space is not None:
        if free_space < DISK_CRITICAL_BYTES:
            findings.append(
                _finding(
                    "disk_critical",
                    "critical",
                    "Critically low free disk space",
                    f"Only {free_space / 1024 / 1024:.0f} MiB free on the save "
                    "volume. qBittorrent pauses or errors torrents when it cannot "
                    "allocate files.",
                )
            )
        elif free_space < DISK_LOW_BYTES:
            findings.append(
                _finding(
                    "disk_low",
                    "warning",
                    "Low free disk space",
                    f"{free_space / 1024 / 1024 / 1024:.1f} GiB free on the save "
                    "volume; large releases may fail to allocate.",
                )
            )
    if errored > 0:
        findings.append(
            _finding(
                "torrents_errored",
                "warning",
                f"{errored} torrent(s) in an error/missing-files state",
                "Error or missingFiles states often indicate disk problems, "
                "permissions issues, or files moved/deleted outside qBittorrent.",
            )
        )

    # --- Global download throttle / disabled --------------------------
    if alt_speed_on:
        detail = "Alternative speed limits are active."
        if dl_limit and dl_limit > 0:
            detail += (
                f" Effective global download limit is {dl_limit / 1024:.0f} KiB/s, "
                "which can starve the queue."
            )
        findings.append(
            _finding(
                "alt_speed_active",
                "info" if not (dl_limit and dl_limit > 0) else "warning",
                "Alternative (throttled) speed limits are active",
                detail
                + " This may be driven by the scheduler during off-hours.",
            )
        )
    if dl_limit is not None and dl_limit > 0 and (dl_speed or 0) == 0 and active > 0:
        findings.append(
            _finding(
                "global_download_throttled",
                "warning",
                "Global download rate limit may be choking downloads",
                f"A global download limit of {dl_limit / 1024:.0f} KiB/s is set "
                "while active downloads show zero throughput.",
            )
        )

    # --- Paused queue behaviour ---------------------------------------
    if paused > 0 and (working + metadata + stalled + queued) == 0:
        findings.append(
            _finding(
                "all_downloads_paused",
                "warning",
                "All downloads are paused/stopped",
                f"{paused} download(s) are paused and none are active. Nothing "
                "will progress until they are resumed.",
            )
        )
    elif paused > 0:
        findings.append(
            _finding(
                "some_downloads_paused",
                "info",
                f"{paused} download(s) paused/stopped",
                "Paused downloads do not occupy queue slots but will not finish "
                "until resumed.",
            )
        )

    # --- Metadata acquisition bottleneck ------------------------------
    metadata_bottleneck = False
    if metadata >= METADATA_MIN_COUNT and (
        (max_active_dl is not None and max_active_dl > 0 and metadata >= max_active_dl)
        or metadata >= working + 1
    ):
        metadata_bottleneck = True
        findings.append(
            _finding(
                "metadata_bottleneck",
                "warning",
                "Metadata acquisition is consuming download slots",
                f"{metadata} torrent(s) are stuck fetching metadata (metaDL). "
                "These hold download slots while contributing no data; if they "
                "cannot reach peers they create a deadlock that blocks real "
                "downloads from starting.",
            )
        )

    # --- Stalled bottleneck -------------------------------------------
    excessive_stalled = False
    if stalled >= STALLED_MIN_COUNT and stalled >= max(2, working):
        excessive_stalled = True
        findings.append(
            _finding(
                "excessive_stalled",
                "warning",
                "Excessive stalled downloads",
                f"{stalled} download(s) are stalled (connected to the queue but "
                f"transferring nothing) versus {working} actively transferring. "
                "Either the releases lack seeds or peers are unreachable.",
            )
        )

    # --- Queue saturation / slot exhaustion ---------------------------
    queue_saturated = False
    slots_exhausted = False
    if slots_full and queued > 0:
        queue_saturated = True
        findings.append(
            _finding(
                "queue_saturated",
                "warning",
                "Queue saturated",
                f"{slots_used} torrent(s) occupy all {max_active_dl} download "
                f"slot(s) and {queued} more are waiting in the queue. Downloads "
                "are serialized; raise max_active_downloads or clear the backlog.",
            )
        )
    elif slots_full:
        slots_exhausted = True
        findings.append(
            _finding(
                "slots_exhausted",
                "info",
                "Download slots exhausted",
                f"All {max_active_dl} download slot(s) are in use "
                f"({slots_used} occupying torrents). New downloads will queue "
                "until a slot frees up.",
            )
        )
        if dont_count_slow:
            findings.append(
                _finding(
                    "slow_torrents_excluded",
                    "info",
                    "Slow torrents excluded from queue limits",
                    "dont_count_slow_torrents is enabled, so stalled/slow "
                    "torrents may not count toward the active-download limit.",
                )
            )

    # --- Pick the primary label (most specific root cause first) -------
    if network_issue:
        primary, severity = "Possible network/VPN issue", "bad"
    elif metadata_bottleneck:
        primary, severity = "Metadata acquisition bottleneck", "warn"
    elif excessive_stalled:
        primary, severity = "Excessive stalled downloads", "warn"
    elif queue_saturated:
        primary, severity = "Queue saturated", "warn"
    elif slots_exhausted:
        primary, severity = "Download slots exhausted", "warn"
    else:
        primary, severity = "Healthy queue", "ok"
        if not findings:
            findings.append(
                _finding(
                    "healthy",
                    "info",
                    "No queue problems detected",
                    "Download slots, connectivity and disk space all look fine.",
                )
            )

    return primary, severity, findings


def queue_report(config: Config) -> dict[str, Any]:
    """Full qBittorrent queue diagnostics: transfer info, preferences, queue and
    connection settings, derived counts, a dashboard summary and a prioritized
    set of findings explaining the likely root cause."""
    if not config.service_enabled(SOURCE):
        return {
            "service": SOURCE,
            "enabled": False,
            "ok": False,
            "error": "service disabled or not configured",
        }

    svc = config.service(SOURCE)
    base_url = str(svc.get("base_url", "")).rstrip("/")
    username = svc.get("username", "")
    password = svc.get("password", "")
    torrents_endpoint = svc.get("torrents_endpoint", "/api/v2/torrents/info")
    transfer_endpoint = svc.get("transfer_info_endpoint", TRANSFER_INFO_ENDPOINT)
    prefs_endpoint = svc.get("preferences_endpoint", PREFERENCES_ENDPOINT)
    speed_mode_endpoint = svc.get("speed_limits_mode_endpoint", SPEED_LIMITS_MODE_ENDPOINT)
    maindata_endpoint = svc.get("maindata_endpoint", MAINDATA_ENDPOINT)

    errors: dict[str, str] = {}
    transfer: dict[str, Any] = {}
    prefs: dict[str, Any] = {}
    server_state: dict[str, Any] = {}
    torrents: list[dict[str, Any]] = []
    alt_speed_on: bool | None = None

    try:
        with httpx.Client(timeout=15.0) as client:
            if not _login(client, base_url, username, password):
                return {
                    "service": SOURCE,
                    "enabled": True,
                    "ok": False,
                    "error": "login failed",
                }

            raw_transfer = _safe_get(client, base_url, transfer_endpoint, errors, "transfer")
            if isinstance(raw_transfer, dict):
                transfer = raw_transfer

            raw_prefs = _safe_get(client, base_url, prefs_endpoint, errors, "preferences")
            if isinstance(raw_prefs, dict):
                prefs = raw_prefs

            raw_mode = _safe_get(client, base_url, speed_mode_endpoint, errors, "speed_mode")
            if raw_mode is not None:
                alt_speed_on = _as_bool(raw_mode)

            raw_main = _safe_get(client, base_url, maindata_endpoint, errors, "maindata")
            if isinstance(raw_main, dict) and isinstance(
                raw_main.get("server_state"), dict
            ):
                server_state = raw_main["server_state"]
                if alt_speed_on is None:
                    alt_speed_on = _as_bool(server_state.get("use_alt_speed_limits"))

            raw_torrents = _safe_get(client, base_url, torrents_endpoint, errors, "torrents")
            if isinstance(raw_torrents, list):
                torrents = [t for t in raw_torrents if isinstance(t, dict)]
            elif raw_torrents is not None:
                errors["torrents"] = "unexpected torrents payload shape (expected a list)"
    except Exception as exc:  # noqa: BLE001
        return {
            "service": SOURCE,
            "enabled": True,
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        }

    counts = _count_states(torrents)
    primary, severity, findings = diagnose_queue(
        counts=counts,
        prefs=prefs,
        transfer=transfer,
        server_state=server_state,
        alt_speed_on=alt_speed_on,
    )

    queue_settings = {
        "queueing_enabled": _as_bool(prefs.get("queueing_enabled")),
        "max_active_downloads": _to_int(prefs.get("max_active_downloads")),
        "max_active_uploads": _to_int(prefs.get("max_active_uploads")),
        "max_active_torrents": _to_int(prefs.get("max_active_torrents")),
        "dont_count_slow_torrents": _as_bool(prefs.get("dont_count_slow_torrents")),
        "slow_torrent_dl_rate_threshold": _to_int(
            prefs.get("slow_torrent_dl_rate_threshold")
        ),
        "slow_torrent_ul_rate_threshold": _to_int(
            prefs.get("slow_torrent_ul_rate_threshold")
        ),
        "slow_torrent_inactive_timer": _to_int(
            prefs.get("slow_torrent_inactive_timer")
        ),
    }
    rate_limits = {
        "global_dl_limit": _to_int(prefs.get("dl_limit")),
        "global_up_limit": _to_int(prefs.get("up_limit")),
        "alt_dl_limit": _to_int(prefs.get("alt_dl_limit")),
        "alt_up_limit": _to_int(prefs.get("alt_up_limit")),
        "transfer_dl_rate_limit": _to_int(transfer.get("dl_rate_limit")),
        "transfer_up_rate_limit": _to_int(transfer.get("up_rate_limit")),
    }
    connection_limits = {
        "max_connec": _to_int(prefs.get("max_connec")),
        "max_connec_per_torrent": _to_int(prefs.get("max_connec_per_torrent")),
        "max_uploads": _to_int(prefs.get("max_uploads")),
        "max_uploads_per_torrent": _to_int(prefs.get("max_uploads_per_torrent")),
    }
    scheduler = {
        "scheduler_enabled": _as_bool(prefs.get("scheduler_enabled")),
        "schedule_from_hour": _to_int(prefs.get("schedule_from_hour")),
        "schedule_from_min": _to_int(prefs.get("schedule_from_min")),
        "schedule_to_hour": _to_int(prefs.get("schedule_to_hour")),
        "schedule_to_min": _to_int(prefs.get("schedule_to_min")),
        "scheduler_days": _to_int(prefs.get("scheduler_days")),
    }
    alt_speed_limits = {
        "active": alt_speed_on,
        "alt_dl_limit": _to_int(prefs.get("alt_dl_limit")),
        "alt_up_limit": _to_int(prefs.get("alt_up_limit")),
    }

    free_space = _to_int(server_state.get("free_space_on_disk"))
    connection_status = (
        transfer.get("connection_status")
        or server_state.get("connection_status")
    )

    summary = {
        "queued_downloads": counts["queued_downloads"],
        "stalled_downloads": counts["stalled_downloads"],
        "active_downloads": counts["active_downloads"],
        "completed_torrents": counts["completed"],
        "health": primary,
        "health_severity": severity,
    }

    return {
        "service": SOURCE,
        "enabled": True,
        "ok": True,
        "error": None,
        "errors": errors,
        "diagnosis": primary,
        "health_severity": severity,
        "summary": summary,
        "findings": findings,
        "counts": counts,
        "transfer_info": transfer,
        "connection_status": connection_status,
        "free_space_on_disk": free_space,
        "queue_settings": queue_settings,
        "rate_limits": rate_limits,
        "connection_limits": connection_limits,
        "scheduler": scheduler,
        "alt_speed_limits": alt_speed_limits,
        "server_state": server_state,
        "preferences": prefs,
    }


def _normalize_torrent_full(t: dict[str, Any]) -> dict[str, Any]:
    """Richer normalized view of a single torrent for the per-torrent report."""
    base = _normalize_torrent(t)
    base.update(
        {
            "upspeed": _to_int(t.get("upspeed")),
            "eta": _to_int(t.get("eta")),
            "priority": _to_int(t.get("priority")),  # queue position; 0 = not queued
            "size": _to_int(t.get("size")),
            "total_size": _to_int(t.get("total_size")),
            "downloaded": _to_int(t.get("downloaded")),
            "uploaded": _to_int(t.get("uploaded")),
            "amount_left": _to_int(t.get("amount_left")),
            "availability": t.get("availability"),
            "category": t.get("category"),
            "tags": t.get("tags"),
            "added_on": _to_int(t.get("added_on")),
            "completion_on": _to_int(t.get("completion_on")),
            "save_path": t.get("save_path"),
            "tracker": t.get("tracker"),
        }
    )
    return base


def _diagnose_torrent(
    norm: dict[str, Any], trackers: list[dict[str, Any]]
) -> list[str]:
    """Per-torrent diagnosis reasons from its state, speed and tracker health."""
    reasons: list[str] = []
    state = (norm.get("state") or "").lower()
    classification = states.classify(state)

    if not state:
        reasons.append("Torrent is missing a 'state' field")
        return reasons

    if states.is_seeding_state(state):
        reasons.append("Completed / seeding — download-health checks do not apply")
        return reasons

    if classification == states.ERROR:
        reasons.append("In an error/missing-files state — check disk and permissions")
    if classification == states.PAUSED:
        reasons.append("Download is paused/stopped and will not progress until resumed")
    if state == "metadl":
        reasons.append(
            "Fetching metadata — cannot reach peers/DHT to learn the file list yet"
        )
    if state == "queueddl":
        reasons.append("Waiting in the download queue (a download slot is not free)")
    if state == "stalleddl":
        reasons.append(
            "Stalled — connected but transferring nothing; likely no reachable seeds"
        )

    peers = norm.get("peers")
    seeds = norm.get("seeds")
    dlspeed = norm.get("dlspeed")
    if states.is_active_download_state(state):
        if (peers or 0) == 0 and (seeds or 0) == 0:
            reasons.append(
                "Zero seeds and zero peers — dead swarm or unreachable network"
            )
        elif (peers or 0) > 0 and (dlspeed or 0) == 0:
            reasons.append(
                "Peers present but zero download speed — queue, disk or peer choking"
            )

    # Tracker health.
    if trackers:
        real = [
            tr
            for tr in trackers
            if isinstance(tr, dict)
            and not str(tr.get("url", "")).startswith("**")
        ]
        working = [tr for tr in real if _to_int(tr.get("status")) == 2]
        if real and not working:
            msgs = sorted({str(tr.get("msg")) for tr in real if tr.get("msg")})
            detail = f" ({'; '.join(msgs)})" if msgs else ""
            reasons.append(f"No working trackers{detail}")

    if not reasons:
        reasons.append("No torrent-level problem detected")
    return reasons


def torrent_report(config: Config, torrent_hash: str) -> dict[str, Any]:
    """Deep dive on a single torrent: normalized data, tracker states, peers,
    speeds, queue position, state classification, diagnosis reasons, how the
    correlator matched it, and raw payload snippets."""
    if not config.service_enabled(SOURCE):
        return {
            "service": SOURCE,
            "enabled": False,
            "ok": False,
            "error": "service disabled or not configured",
        }

    target = (torrent_hash or "").strip().lower()
    if not target:
        return {"service": SOURCE, "ok": False, "error": "no torrent hash supplied"}

    svc = config.service(SOURCE)
    base_url = str(svc.get("base_url", "")).rstrip("/")
    username = svc.get("username", "")
    password = svc.get("password", "")
    torrents_endpoint = svc.get("torrents_endpoint", "/api/v2/torrents/info")
    trackers_endpoint = svc.get("trackers_endpoint", "/api/v2/torrents/trackers")
    properties_endpoint = svc.get("properties_endpoint", PROPERTIES_ENDPOINT)
    peers_endpoint = svc.get("peers_endpoint", PEERS_ENDPOINT)

    errors: dict[str, str] = {}
    raw_torrent: dict[str, Any] | None = None
    trackers: list[dict[str, Any]] = []
    properties: dict[str, Any] = {}
    peers: dict[str, Any] = {}

    try:
        with httpx.Client(timeout=15.0) as client:
            if not _login(client, base_url, username, password):
                return {
                    "service": SOURCE,
                    "enabled": True,
                    "ok": False,
                    "error": "login failed",
                }

            raw_list = _safe_get(
                client,
                base_url,
                torrents_endpoint,
                errors,
                "torrents",
                params={"hashes": target},
            )
            if isinstance(raw_list, list):
                for t in raw_list:
                    if isinstance(t, dict) and str(t.get("hash", "")).lower() == target:
                        raw_torrent = t
                        break

            raw_trackers = _safe_get(
                client,
                base_url,
                trackers_endpoint,
                errors,
                "trackers",
                params={"hash": target},
            )
            if isinstance(raw_trackers, list):
                trackers = [tr for tr in raw_trackers if isinstance(tr, dict)]

            raw_props = _safe_get(
                client,
                base_url,
                properties_endpoint,
                errors,
                "properties",
                params={"hash": target},
            )
            if isinstance(raw_props, dict):
                properties = raw_props

            raw_peers = _safe_get(
                client,
                base_url,
                peers_endpoint,
                errors,
                "peers",
                params={"hash": target},
            )
            if isinstance(raw_peers, dict) and isinstance(raw_peers.get("peers"), dict):
                peers = raw_peers["peers"]
    except Exception as exc:  # noqa: BLE001
        return {
            "service": SOURCE,
            "enabled": True,
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        }

    if raw_torrent is None:
        return {
            "service": SOURCE,
            "enabled": True,
            "ok": False,
            "error": f"no torrent found with hash {target}",
            "errors": errors,
        }

    norm = _normalize_torrent_full(raw_torrent)
    state = norm.get("state")

    tracker_states = [
        {
            "url": tr.get("url"),
            "status": _to_int(tr.get("status")),
            "status_label": TRACKER_STATUS.get(_to_int(tr.get("status")), "unknown"),
            "num_peers": _to_int(tr.get("num_peers")),
            "num_seeds": _to_int(tr.get("num_seeds")),
            "num_leeches": _to_int(tr.get("num_leeches")),
            "msg": tr.get("msg"),
        }
        for tr in trackers
    ]

    peer_list = [
        {
            "ip": info.get("ip"),
            "port": _to_int(info.get("port")),
            "client": info.get("client"),
            "connection": info.get("connection"),
            "country": info.get("country"),
            "progress": info.get("progress"),
            "dl_speed": _to_int(info.get("dl_speed")),
            "up_speed": _to_int(info.get("up_speed")),
        }
        for info in peers.values()
        if isinstance(info, dict)
    ]

    # How did the correlator match this torrent (if at all)?
    match_source = None
    match_reasons: list[str] = []
    matched_title = None
    try:
        from ..correlation import correlation_report

        for entry in correlation_report(config):
            if (entry.get("torrent_hash") or "").lower() == target:
                match_source = entry.get("match_source")
                match_reasons = entry.get("match_reasons") or []
                matched_title = entry.get("title")
                break
    except Exception as exc:  # noqa: BLE001
        errors["correlation"] = f"{type(exc).__name__}: {exc}"

    return {
        "service": SOURCE,
        "enabled": True,
        "ok": True,
        "error": None,
        "errors": errors,
        "hash": target,
        "normalized": norm,
        "state": state,
        "state_classification": states.classify(state),
        "is_active_download": states.is_active_download_state(state),
        "is_seeding": states.is_seeding_state(state),
        "queue_position": norm.get("priority"),
        "speeds": {
            "dlspeed": norm.get("dlspeed"),
            "upspeed": norm.get("upspeed"),
            "eta": norm.get("eta"),
        },
        "tracker_states": tracker_states,
        "peers": peer_list,
        "peer_count": len(peer_list),
        "diagnosis_reasons": _diagnose_torrent(norm, trackers),
        "match_source": match_source,
        "matched_title": matched_title,
        "match_reasons": match_reasons,
        "raw": {
            "torrent": raw_torrent,
            "properties": properties,
            "trackers": trackers[:10],
            "peers_sample": peer_list[:10],
        },
    }
