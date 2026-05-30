"""Local library artifact collector.

Observes configured library roots and expected import destinations using
read-only filesystem calls. It never creates, modifies, or deletes files.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

from .. import db
from ..config import Config

logger = logging.getLogger("handoffarr.collectors.library")

SOURCE = "library"
_WORD_RE = re.compile(r"[a-z0-9]+")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_id(media_id: str | None, path: str | None, title: str | None) -> str:
    basis = "|".join(str(part or "") for part in (media_id, path, title))
    digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:20]
    return f"library:{digest}"


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


def _configured_roots(config: Config) -> list[dict[str, Any]]:
    library = config.section("library")
    if not library.get("enabled", False):
        return []
    roots = library.get("roots") or library.get("root_folders") or []
    if not isinstance(roots, list):
        return []
    normalized: list[dict[str, Any]] = []
    for root in roots:
        if isinstance(root, str):
            path = root.strip()
            if path:
                normalized.append({"path": path})
        elif isinstance(root, dict) and root.get("path"):
            normalized.append(root)
    return normalized


def _normalize_prefix(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text.rstrip("/\\")


def _collect_mappings(raw: Any) -> list[tuple[str, str]]:
    mappings: list[tuple[str, str]] = []
    if not isinstance(raw, list):
        return mappings
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        src = _normalize_prefix(entry.get("from") or entry.get("source") or entry.get("container"))
        dst = _normalize_prefix(entry.get("to") or entry.get("target") or entry.get("host"))
        if src and dst:
            mappings.append((src, dst))
    # Longest source prefix first so nested mappings win over shallow ones.
    mappings.sort(key=lambda pair: len(pair[0]), reverse=True)
    return mappings


def _path_mappings(config: Config, source_application: str | None) -> list[tuple[str, str]]:
    library = config.section("library")
    mappings = _collect_mappings(library.get("path_mappings"))
    for service_name in ("radarr", "sonarr", "lidarr"):
        if source_application and service_name != source_application.lower():
            continue
        mappings.extend(_collect_mappings(config.service(service_name).get("path_mappings")))
    seen: set[tuple[str, str]] = set()
    unique: list[tuple[str, str]] = []
    for pair in mappings:
        if pair in seen:
            continue
        seen.add(pair)
        unique.append(pair)
    unique.sort(key=lambda pair: len(pair[0]), reverse=True)
    return unique


def _apply_mappings(path: str, mappings: list[tuple[str, str]]) -> tuple[str, tuple[str, str] | None]:
    if not path:
        return path, None
    normalized = path.replace("\\", "/")
    for src, dst in mappings:
        src_norm = src.replace("\\", "/")
        if normalized == src_norm or normalized.startswith(src_norm + "/"):
            remainder = normalized[len(src_norm):]
            mapped = dst.rstrip("/\\") + remainder
            return mapped, (src, dst)
    return path, None


def _is_under_root(path: str, roots: list[dict[str, Any]]) -> bool:
    if not roots:
        return True
    abs_path = os.path.abspath(path)
    for root in roots:
        root_path = os.path.abspath(str(root.get("path")))
        try:
            if os.path.commonpath([abs_path, root_path]) == root_path:
                return True
        except ValueError:
            continue
    return False


def _file_size(path: str) -> int | None:
    if os.path.isfile(path):
        return os.path.getsize(path)
    if not os.path.isdir(path):
        return None
    total = 0
    for root, dirs, files in os.walk(path, followlinks=False):
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
        for filename in files:
            full_path = os.path.join(root, filename)
            try:
                if not os.path.islink(full_path):
                    total += os.path.getsize(full_path)
            except OSError:
                continue
    return total


def _find_title_path(
    title: str | None,
    roots: list[dict[str, Any]],
    max_entries: int,
) -> tuple[str | None, str | None]:
    normalized_title = _normalize_title(title)
    if not normalized_title:
        return None, "no media title available for library search"

    title_words = set(normalized_title.split())
    scanned = 0
    for root in roots:
        root_path = os.path.abspath(str(root.get("path")))
        if not os.path.isdir(root_path):
            continue
        for current_root, dirs, files in os.walk(root_path, followlinks=False):
            scanned += 1
            if scanned > max_entries:
                return None, f"library title search stopped after {max_entries} entries"
            candidates = list(dirs) + files
            for name in candidates:
                words = set(_normalize_title(name).split())
                if title_words and title_words.issubset(words):
                    return os.path.join(current_root, name), None
    return None, "no matching library path found under configured roots"


def _artifact_from_import(
    import_event: dict[str, Any],
    roots: list[dict[str, Any]],
    observed_at: str,
    max_entries: int,
    mappings: list[tuple[str, str]],
) -> dict[str, Any]:
    media_id = str(import_event.get("media_id") or import_event.get("import_id") or "")
    title = import_event.get("media_title")
    destination = import_event.get("destination_path")
    raw_path = str(destination) if destination else None
    mapping_used: tuple[str, str] | None = None
    if raw_path:
        mapped, mapping_used = _apply_mappings(raw_path, mappings)
        path = os.path.abspath(mapped)
        path_source = (
            "import_destination_path_mapped" if mapping_used else "import_destination_path"
        )
    else:
        path = None
        path_source = None
    search_note = None

    if path and not mapping_used and not _is_under_root(path, roots):
        search_note = "destination path is outside configured library roots"
    if not path:
        path, search_note = _find_title_path(title, roots, max_entries)
        path_source = "title_search" if path else None

    exists = bool(path and os.path.exists(path))
    size = _file_size(path) if exists and path else None
    evidence = {
        "source": SOURCE,
        "import_id": import_event.get("import_id"),
        "import_status": import_event.get("import_status"),
        "path_source": path_source,
        "path_verified": exists,
        "message": (
            "Library path verified."
            if exists
            else "Expected library path was not found."
            if path
            else "No library path could be determined."
        ),
    }
    if mapping_used:
        evidence["path_mapping"] = {"from": mapping_used[0], "to": mapping_used[1]}
        evidence["destination_path"] = raw_path
    if search_note:
        evidence["note"] = search_note

    return {
        "artifact_id": _stable_id(media_id, path, title),
        "media_id": media_id,
        "media_title": title,
        "media_type": import_event.get("media_type"),
        "library_path": path,
        "file_exists": exists,
        "file_size": size,
        "source_application": import_event.get("source_application"),
        "observed_at": observed_at,
        "evidence": evidence,
    }


def collect(config: Config) -> int:
    """Observe configured library paths and persist raw library events."""
    roots = _configured_roots(config)
    if not roots:
        logger.debug("Library collector disabled or no library roots configured")
        return 0

    library = config.section("library")
    max_entries = int(library.get("max_scan_entries", 5000))
    observed_at = _utcnow()
    stored = 0

    for import_event in db.all_import_events():
        mappings = _path_mappings(config, import_event.get("source_application"))
        artifact = _artifact_from_import(
            import_event, roots, observed_at, max_entries, mappings
        )
        db.insert_raw_event(
            source=SOURCE,
            event_type="artifact",
            external_id=artifact["artifact_id"],
            title=artifact.get("media_title"),
            torrent_hash=None,
            download_id=None,
            payload=artifact,
            observed_at=observed_at,
        )
        stored += 1

    logger.info("Library collector stored %d events", stored)
    return stored


def inspect(config: Config) -> dict[str, Any]:
    roots = _configured_roots(config)
    observed_at = _utcnow()
    max_entries = int(config.section("library").get("max_scan_entries", 5000))
    artifacts = [
        _artifact_from_import(
            import_event,
            roots,
            observed_at,
            max_entries,
            _path_mappings(config, import_event.get("source_application")),
        )
        for import_event in db.all_import_events()
    ]
    return {
        "service": SOURCE,
        "enabled": bool(roots),
        "ok": True,
        "roots": roots,
        "artifacts": artifacts,
    }
