"""Read-only import-history diagnostics."""

from __future__ import annotations

from typing import Any

from .collectors import lidarr_imports, radarr_imports, sonarr_imports
from .collectors.import_history import (
    IMPORT_FAILURE_EVENTS,
    IMPORT_SUCCESS_EVENTS,
    KNOWN_NON_IMPORT_EVENTS,
    canonical_event_type,
    classify_record,
    has_import_artifacts,
    resolve_event_type,
)
from .config import Config


COLLECTORS = (
    ("sonarr", sonarr_imports),
    ("radarr", radarr_imports),
    ("lidarr", lidarr_imports),
)
DEFAULT_ENDPOINTS = {
    "sonarr": "/api/v3/history",
    "radarr": "/api/v3/history",
    "lidarr": "/api/v1/history",
}


def _service_debug(config: Config, name: str, collector: Any) -> dict[str, Any]:
    svc = config.service(name)
    ok, error, raw, records = collector.fetch_history_raw(config)
    recognized: list[dict[str, Any]] = []
    discarded: list[dict[str, Any]] = []

    for record in records:
        status, basis = classify_record(record, name)
        resolved = resolve_event_type(record, name)
        canonical = canonical_event_type(resolved)
        if status is None:
            discarded.append(
                {
                    "id": record.get("id"),
                    "eventType": record.get("eventType"),
                    "resolved_event_type": resolved,
                    "canonical_event_type": canonical,
                    "sourceTitle": record.get("sourceTitle"),
                    "date": record.get("date"),
                    "discard_reason": basis,
                    "has_import_artifacts": has_import_artifacts(record),
                    "data_keys": sorted((record.get("data") or {}).keys())
                    if isinstance(record.get("data"), dict)
                    else [],
                    "raw": record,
                }
            )
            continue
        normalized = collector.normalize_record(record)
        normalized["classification_basis"] = basis
        normalized["resolved_event_type"] = resolved
        recognized.append(normalized)

    return {
        "service": name,
        "enabled": config.service_enabled(name),
        "url": f"{str(svc.get('base_url', '')).rstrip('/')}"
        f"{svc.get('history_endpoint', DEFAULT_ENDPOINTS[name])}",
        "configured_endpoint": svc.get("history_endpoint"),
        "ok": ok,
        "error": error,
        "raw_import_history_records": records,
        "recognized_import_records": recognized,
        "recognized_count": len(recognized),
        "discarded_count": len(discarded),
        "discarded_records": discarded,
        "raw_response": raw,
    }


def inspect_imports(config: Config) -> dict[str, Any]:
    return {
        "supported_event_types": {
            "success": sorted(IMPORT_SUCCESS_EVENTS),
            "failure": sorted(IMPORT_FAILURE_EVENTS),
            "known_non_import": sorted(KNOWN_NON_IMPORT_EVENTS),
            "requested": {
                "downloadFolderImported": "recognized_success",
                "grabbed": "discarded_non_import_history_event",
                "imported": "recognized_success",
                "downloadImported": "recognized_success",
                "rename": "discarded_non_import_history_event",
            },
        },
        "services": [
            _service_debug(config, name, collector) for name, collector in COLLECTORS
        ],
    }
