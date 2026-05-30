"""Shared helpers for *arr import-history collectors."""

from __future__ import annotations

import re
from typing import Any

IMPORT_SUCCESS_EVENTS = {
    "albumimported",
    "downloadfolderimported",
    "downloadimported",
    "episodefileimported",
    "imported",
    "moviefileimported",
    "trackfileimported",
}
IMPORT_FAILURE_EVENTS = {"downloadfailed", "importfailed"}
KNOWN_NON_IMPORT_EVENTS = {
    "grabbed",
    "rename",
    "renamed",
    "moviefilerenamed",
    "episodefilerenamed",
    "trackfilerenamed",
    "moviefiledeleted",
    "episodefiledeleted",
    "trackfiledeleted",
    "downloadignored",
    "movieadded",
    "seriesadded",
    "artistadded",
}

# Radarr/Sonarr/Lidarr HistoryEventType enums.  Some deployments (older API
# versions, certain reverse proxies, JSON serializers) return ``eventType`` as
# the integer enum value instead of the canonical string label, which the
# previous recognition layer silently discarded as ``unsupported_event_type``.
NUMERIC_EVENT_TYPES: dict[str, dict[int, str]] = {
    "radarr": {
        1: "grabbed",
        2: "downloadFolderImported",
        3: "downloadFolderImported",
        4: "downloadFailed",
        5: "movieFileDeleted",
        6: "movieFolderImported",
        7: "movieFileRenamed",
        8: "downloadIgnored",
        9: "movieFileImported",
    },
    "sonarr": {
        1: "grabbed",
        2: "seriesFolderImported",
        3: "downloadFolderImported",
        4: "downloadFailed",
        5: "episodeFileDeleted",
        6: "downloadIgnored",
        7: "episodeFileRenamed",
        8: "episodeFileImported",
        9: "episodeFileImported",
    },
    "lidarr": {
        1: "grabbed",
        2: "downloadFolderImported",
        3: "downloadImported",
        4: "downloadFailed",
        5: "trackFileDeleted",
        6: "trackFileRenamed",
        7: "trackFileImported",
        8: "albumImported",
    },
}

# Field names whose presence inside the history record (or its ``data`` block)
# is unambiguous evidence that the *arr application is reporting an imported
# artifact.  Used as a last-resort recognition signal when the eventType label
# is unfamiliar but the payload clearly describes a completed import.
IMPORT_ARTIFACT_DATA_KEYS = (
    "importedPath",
    "destinationPath",
    "movieFilePath",
    "episodeFilePath",
    "trackFilePath",
    "filePath",
    "fileId",
)
IMPORT_ARTIFACT_NESTED_KEYS = ("movieFile", "episodeFile", "trackFile", "file")


def canonical_event_type(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _data(record: dict[str, Any]) -> dict[str, Any]:
    data = record.get("data")
    return data if isinstance(data, dict) else {}


def resolve_event_type(record: dict[str, Any], source: str | None = None) -> Any:
    """Return the most plausible raw eventType for ``record``.

    Looks at the top-level ``eventType``, falls back to ``data.eventType``, and
    finally maps a numeric enum value to the canonical *arr string label when a
    ``source`` hint is supplied.
    """

    for value in (record.get("eventType"), _data(record).get("eventType")):
        if value in (None, ""):
            continue
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            mapped = NUMERIC_EVENT_TYPES.get((source or "").lower(), {}).get(value)
            if mapped:
                return mapped
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                continue
            if stripped.isdigit():
                mapped = NUMERIC_EVENT_TYPES.get((source or "").lower(), {}).get(
                    int(stripped)
                )
                if mapped:
                    return mapped
            return stripped
        return value
    return None


def has_import_artifacts(record: dict[str, Any]) -> bool:
    data = _data(record)
    for key in IMPORT_ARTIFACT_DATA_KEYS:
        value = data.get(key)
        if value not in (None, "", 0):
            return True
    for key in IMPORT_ARTIFACT_NESTED_KEYS:
        nested = record.get(key)
        if isinstance(nested, dict) and nested.get("path"):
            return True
    return False


def import_status_for_event(event_type: Any) -> str | None:
    canonical = canonical_event_type(event_type)
    if canonical in IMPORT_SUCCESS_EVENTS:
        return "Import Success"
    if canonical in IMPORT_FAILURE_EVENTS:
        return "Import Failed"
    return None


def classify_record(
    record: dict[str, Any], source: str | None = None
) -> tuple[str | None, str]:
    """Classify a history record.

    Returns ``(import_status, basis)`` where ``import_status`` is one of
    ``"Import Success"``, ``"Import Failed"`` or ``None`` (record should be
    discarded), and ``basis`` is a short string describing which signal drove
    the decision (useful for the debug endpoint).
    """

    raw_event = resolve_event_type(record, source)
    canonical = canonical_event_type(raw_event)
    status = import_status_for_event(canonical)
    if status == "Import Success":
        return status, f"event_type:{canonical}"
    if status == "Import Failed":
        return status, f"event_type:{canonical}"
    if canonical in KNOWN_NON_IMPORT_EVENTS:
        return None, f"non_import:{canonical}"
    if has_import_artifacts(record):
        return "Import Success", "artifact_inferred"
    if not canonical:
        return None, "missing_event_type"
    return None, f"unsupported_event_type:{raw_event}"


def discard_reason(record: dict[str, Any], source: str | None = None) -> str | None:
    status, basis = classify_record(record, source)
    if status is not None:
        return None
    return basis


def nested_path(record: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = record.get(key)
        if isinstance(value, dict) and value.get("path"):
            return str(value["path"])
    return None
