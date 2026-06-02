"""Configuration loading for Handoffarr.

Loads YAML from /config/config.yaml. If the file is missing the app must still
start safely; callers can check ``config.is_present`` and surface a clear
message on the dashboard instead of crashing.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import yaml

logger = logging.getLogger("handoffarr.config")

CONFIG_PATH = os.environ.get("HANDOFFARR_CONFIG", "/config/config.yaml")

# Defaults used when a section or key is absent. Kept in sync with
# config.example.yaml so the app behaves sensibly with partial configs.
DEFAULTS: dict[str, Any] = {
    "app": {
        "poll_interval_seconds": 15,
        "lookback_minutes": 120,
        "stale_peer_minutes": 10,
    },
    "thresholds": {
        "low_reported_seeds": 5,
        "healthy_reported_seeds": 20,
        "actual_peers_zero_minutes": 5,
    },
    "storage": {
        "enabled": False,
        "volumes": [],
        "thresholds": {
            "critical_free_bytes": 1073741824,
            "warning_free_bytes": 10737418240,
            "completed_torrent_count": 25,
            "retained_bytes": 107374182400,
        },
    },
    "library": {
        "enabled": False,
        "roots": [],
        "max_scan_entries": 5000,
    },
    "cleanup": {
        "thresholds": {
            "failure_after_hours": 24,
            "retention_min_ratio": None,
        },
    },
    "cleanup_review": {
        "enabled": True,
        "max_file_checks_per_poll": 200,
        "file_size_tolerance_bytes": 10485760,
    },
    "matching": {
        "prefer_torrent_hash": True,
        "fallback_to_download_id": True,
        "fallback_to_normalized_title": True,
        "title_time_window_minutes": 60,
    },
    "services": {},
}


class Config:
    """Wrapper around the parsed YAML config with safe accessors."""

    def __init__(self, data: dict[str, Any] | None, path: str, is_present: bool):
        self._data = data or {}
        self.path = path
        self.is_present = is_present

    def section(self, name: str) -> dict[str, Any]:
        defaults = DEFAULTS.get(name, {})
        value = self._data.get(name) or {}
        if isinstance(defaults, dict) and isinstance(value, dict):
            merged = dict(defaults)
            merged.update(value)
            return merged
        return value

    @property
    def app(self) -> dict[str, Any]:
        return self.section("app")

    @property
    def thresholds(self) -> dict[str, Any]:
        return self.section("thresholds")

    @property
    def matching(self) -> dict[str, Any]:
        return self.section("matching")

    def service(self, name: str) -> dict[str, Any]:
        services = self._data.get("services") or {}
        return services.get(name) or {}

    def service_enabled(self, name: str) -> bool:
        svc = self.service(name)
        return bool(svc.get("enabled")) and bool(svc.get("base_url"))


def load_config(path: str | None = None) -> Config:
    """Load config from disk, tolerating a missing or malformed file."""
    path = path or CONFIG_PATH
    if not os.path.exists(path):
        logger.warning("Config file not found at %s; starting in degraded mode", path)
        return Config(None, path, is_present=False)

    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        if not isinstance(data, dict):
            logger.error("Config at %s is not a mapping; ignoring", path)
            return Config(None, path, is_present=False)
        return Config(data, path, is_present=True)
    except Exception as exc:  # noqa: BLE001 - never crash on bad config
        logger.error("Failed to parse config at %s: %s", path, exc)
        return Config(None, path, is_present=False)
