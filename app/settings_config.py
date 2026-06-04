"""Allowlisted, typed configuration reads and writes for Settings."""

from __future__ import annotations

import os
import tempfile
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .config import Config, DEFAULTS, load_config


class SettingsWriteError(RuntimeError):
    """Raised when the config file cannot be safely updated."""


class CleanupExecutionSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    allow_single_item_execution: bool
    allow_batch_execution: bool
    require_confirmation_phrase: bool
    require_batch_dry_run: bool
    max_items_per_request: Literal[1]
    max_batch_items: int = Field(ge=1, le=1000)


class StorageThresholdSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    critical_free_bytes: int = Field(ge=1)
    warning_free_bytes: int = Field(ge=1)
    completed_torrent_count: int = Field(ge=0, le=1_000_000)
    retained_bytes: int = Field(ge=0)

    @model_validator(mode="after")
    def warning_exceeds_critical(self) -> "StorageThresholdSettings":
        if self.warning_free_bytes <= self.critical_free_bytes:
            raise ValueError("warning_free_bytes must be greater than critical_free_bytes")
        return self


def settings_response(config: Config) -> dict[str, Any]:
    cleanup_defaults = DEFAULTS["cleanup_execution"]
    cleanup = config.section("cleanup_execution")
    storage = config.section("storage")
    configured_thresholds = storage.get("thresholds") or {}
    threshold_defaults = DEFAULTS["storage"]["thresholds"]
    thresholds = {**threshold_defaults, **configured_thresholds}
    return {
        "cleanup": CleanupExecutionSettings(
            **{key: cleanup.get(key, cleanup_defaults[key]) for key in CleanupExecutionSettings.model_fields}
        ).model_dump(),
        "storage": StorageThresholdSettings(
            **{key: thresholds[key] for key in StorageThresholdSettings.model_fields}
        ).model_dump(),
        "restart_required": False,
    }


def _read_raw(path: str) -> dict[str, Any]:
    if not os.path.exists(path):
        raise SettingsWriteError(f"Config file not found at {path}")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
    except Exception as exc:  # noqa: BLE001
        raise SettingsWriteError(f"Could not read config: {exc}") from exc
    if not isinstance(raw, dict):
        raise SettingsWriteError("Config root must be a mapping")
    return raw


def _atomic_write(path: str, raw: dict[str, Any]) -> Config:
    directory = os.path.dirname(path) or "."
    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=directory,
            prefix=".config.",
            suffix=".yaml.tmp",
            delete=False,
        ) as handle:
            temp_path = handle.name
            yaml.safe_dump(raw, handle, sort_keys=False, default_flow_style=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, os.stat(path).st_mode)
        os.replace(temp_path, path)
    except Exception as exc:  # noqa: BLE001
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise SettingsWriteError(f"Could not persist config: {exc}") from exc

    updated = load_config(path)
    if not updated.is_present:
        raise SettingsWriteError("Updated config could not be reloaded")
    return updated


def update_cleanup(config: Config, payload: CleanupExecutionSettings) -> Config:
    raw = _read_raw(config.path)
    current = raw.get("cleanup_execution")
    section = dict(current) if isinstance(current, dict) else {}
    section.update(payload.model_dump())
    raw["cleanup_execution"] = section
    return _atomic_write(config.path, raw)


def update_storage(config: Config, payload: StorageThresholdSettings) -> Config:
    raw = _read_raw(config.path)
    current_storage = raw.get("storage")
    storage = dict(current_storage) if isinstance(current_storage, dict) else {}
    current_thresholds = storage.get("thresholds")
    thresholds = dict(current_thresholds) if isinstance(current_thresholds, dict) else {}
    thresholds.update(payload.model_dump())
    storage["thresholds"] = thresholds
    raw["storage"] = storage
    return _atomic_write(config.path, raw)
