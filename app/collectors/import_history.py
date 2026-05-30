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
KNOWN_NON_IMPORT_EVENTS = {"grabbed", "rename", "renamed"}


def canonical_event_type(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def import_status_for_event(event_type: str) -> str | None:
    canonical = canonical_event_type(event_type)
    if canonical in IMPORT_SUCCESS_EVENTS:
        return "Import Success"
    if canonical in IMPORT_FAILURE_EVENTS:
        return "Import Failed"
    return None


def discard_reason(record: dict[str, Any]) -> str | None:
    event_type = canonical_event_type(record.get("eventType"))
    if import_status_for_event(event_type):
        return None
    if event_type in KNOWN_NON_IMPORT_EVENTS:
        return "non_import_history_event"
    if not event_type:
        return "missing_event_type"
    return f"unsupported_event_type:{record.get('eventType')}"


def nested_path(record: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = record.get(key)
        if isinstance(value, dict) and value.get("path"):
            return str(value["path"])
    return None

