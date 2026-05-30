"""Local filesystem collector.

Observes configured storage paths using read-only filesystem calls and persists
volume/folder snapshots as raw events. It never creates, modifies, or deletes
files.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
from datetime import datetime, timezone
from typing import Any

from .. import db
from ..config import Config

logger = logging.getLogger("handoffarr.collectors.filesystem")

SOURCE = "filesystem"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_id(kind: str, path: str) -> str:
    digest = hashlib.sha1(os.path.abspath(path).encode("utf-8")).hexdigest()[:16]
    return f"{kind}:{digest}"


def _folder_size(path: str) -> tuple[int, list[str]]:
    total = 0
    errors: list[str] = []
    for root, dirs, files in os.walk(path, followlinks=False):
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
        for filename in files:
            full_path = os.path.join(root, filename)
            try:
                if not os.path.islink(full_path):
                    total += os.path.getsize(full_path)
            except OSError as exc:
                errors.append(f"{full_path}: {exc}")
    return total, errors[:25]


def _configured_volumes(config: Config) -> list[dict[str, Any]]:
    storage = config.section("storage")
    if not storage.get("enabled", False):
        return []
    volumes = storage.get("volumes") or []
    if not isinstance(volumes, list):
        return []
    return [v for v in volumes if isinstance(v, dict) and v.get("path")]


def _observe_volume(volume: dict[str, Any], observed_at: str) -> list[dict[str, Any]]:
    label = str(volume.get("label") or volume.get("path"))
    path = os.path.abspath(str(volume.get("path")))
    observations: list[dict[str, Any]] = []

    exists = os.path.exists(path)
    volume_payload: dict[str, Any] = {
        "label": label,
        "path": path,
        "exists": exists,
        "observed_at": observed_at,
    }
    if exists:
        try:
            usage = shutil.disk_usage(path)
            volume_payload.update(
                {
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free,
                }
            )
        except OSError as exc:
            volume_payload["error"] = str(exc)
    else:
        volume_payload["error"] = "path does not exist"

    observations.append(
        {
            "event_type": "volume",
            "external_id": _stable_id("volume", path),
            "title": label,
            "payload": volume_payload,
        }
    )

    if not exists or not os.path.isdir(path):
        return observations

    size_bytes, errors = _folder_size(path)
    child_folders: list[dict[str, Any]] = []
    try:
        children = sorted(os.scandir(path), key=lambda entry: entry.name.lower())
        for entry in children:
            if entry.is_dir(follow_symlinks=False):
                child_size, child_errors = _folder_size(entry.path)
                child_folders.append(
                    {
                        "name": entry.name,
                        "path": os.path.abspath(entry.path),
                        "size_bytes": child_size,
                        "errors": child_errors,
                    }
                )
    except OSError as exc:
        errors.append(f"{path}: {exc}")

    observations.append(
        {
            "event_type": "artifact",
            "external_id": _stable_id("artifact", path),
            "title": label,
            "payload": {
                "label": label,
                "path": path,
                "artifact_type": "folder",
                "size_bytes": size_bytes,
                "child_folders": child_folders,
                "errors": errors,
                "observed_at": observed_at,
            },
        }
    )
    return observations


def collect(config: Config) -> int:
    """Observe configured storage paths and persist raw filesystem events."""
    volumes = _configured_volumes(config)
    if not volumes:
        logger.debug("Filesystem collector disabled or no storage volumes configured")
        return 0

    observed_at = _utcnow()
    stored = 0
    for volume in volumes:
        for observation in _observe_volume(volume, observed_at):
            db.insert_raw_event(
                source=SOURCE,
                event_type=observation["event_type"],
                external_id=observation["external_id"],
                title=observation["title"],
                torrent_hash=None,
                download_id=None,
                payload=observation["payload"],
                observed_at=observed_at,
            )
            stored += 1

    logger.info("Filesystem collector stored %d events", stored)
    return stored


def inspect(config: Config) -> dict[str, Any]:
    """Debug-style read-only view without persisting observations."""
    volumes = _configured_volumes(config)
    observed_at = _utcnow()
    observations: list[dict[str, Any]] = []
    for volume in volumes:
        observations.extend(_observe_volume(volume, observed_at))
    return {
        "service": SOURCE,
        "enabled": bool(volumes),
        "ok": True,
        "observations": observations,
    }
