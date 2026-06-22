"""Durable read projections for expensive API views."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from . import db
from .cleanup_reconciliation import latest_completed_execution_index, matching_completed_execution
from .cleanup_review import build_cleanup_review, summarize_cleanup_review
from .config import Config
from .library import enrich_library_artifacts, summarize_library

CLEANUP_REVIEW_KEY = "cleanup_review:v2"
LIBRARY_ENRICHED_KEY = "library_enriched:v1"


def _fingerprint(parts: list[dict[str, Any]], extra: dict[str, Any] | None = None) -> str:
    payload = {"parts": parts, "extra": extra or {}}
    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def cleanup_review_fingerprint(config: Config) -> str:
    return _fingerprint(
        [
            db.table_fingerprint("cleanup_events"),
            db.table_fingerprint("import_events"),
            db.table_fingerprint("library_artifacts"),
            db.table_fingerprint("handoff_traces"),
            db.completed_cleanup_execution_fingerprint(),
            db.raw_event_fingerprint("cleanup", "file_evidence"),
        ],
        {
            "cleanup_review": config.section("cleanup_review"),
            "cleanup_execution": config.section("cleanup_execution"),
        },
    )


def library_enriched_fingerprint(config: Config) -> str:
    lookback_minutes = int(config.app.get("lookback_minutes", 120))
    return _fingerprint(
        [
            db.table_fingerprint("library_artifacts"),
            db.table_fingerprint("import_events"),
            db.raw_event_fingerprint("qbittorrent"),
        ],
        {
            "library": config.section("library"),
            "lookback_minutes": lookback_minutes,
        },
    )


def _metadata(snapshot: dict[str, Any] | None, fingerprint: str) -> dict[str, Any]:
    if snapshot is None:
        return {
            "generated_at": None,
            "source_event_count": 0,
            "stale": True,
            "refresh_required": True,
        }
    stale = snapshot.get("fingerprint") != fingerprint
    return {
        "generated_at": snapshot.get("generated_at"),
        "source_event_count": snapshot.get("source_event_count") or 0,
        "stale": stale,
        "refresh_required": stale,
    }


def _cleanup_execution_reconciliation_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    completed_index = latest_completed_execution_index(db.all_cleanup_executions(limit=5000))
    completed_hashes = set((completed_index.get("by_hash") or {}).keys())
    offenders: list[dict[str, Any]] = []
    for item in items:
        if item.get("review_class") not in {"Safe Review Candidate", "Risky Review Candidate"}:
            continue
        matched = matching_completed_execution(item, completed_index)
        if not matched:
            continue
        offenders.append(
            {
                "media_id": item.get("media_id"),
                "media_title": item.get("media_title"),
                "qbit_hash": item.get("qbit_hash") or item.get("torrent_hash"),
                "review_class": item.get("review_class"),
                "recoverable_bytes": item.get("recoverable_bytes"),
                "execution_id": matched.get("execution_id"),
            }
        )
    return {
        "completed_execution_hashes": len(completed_hashes),
        "offender_count": len(offenders),
        "offenders": offenders[:10],
    }


def rebuild_cleanup_review_projection(config: Config) -> dict[str, Any]:
    fingerprint = cleanup_review_fingerprint(config)
    snapshot = db.projection_snapshot(CLEANUP_REVIEW_KEY)
    if snapshot and snapshot.get("fingerprint") == fingerprint:
        items = snapshot.get("payload") if isinstance(snapshot.get("payload"), list) else []
        summary = snapshot.get("summary") if isinstance(snapshot.get("summary"), dict) else {}
        return {
            "items": items,
            "summary": summary,
            "projection": _metadata(snapshot, fingerprint),
        }

    cleanup_events = db.all_cleanup_events()
    import_events = db.all_import_events()
    library_artifacts = db.all_library_artifacts()
    traces = db.all_traces()
    items = build_cleanup_review(
        cleanup_events,
        import_events,
        library_artifacts,
        traces,
        config,
    )
    summary = summarize_cleanup_review(items)
    summary["completed_execution_reconciliation"] = (
        _cleanup_execution_reconciliation_summary(items)
    )
    db.upsert_projection_snapshot(
        CLEANUP_REVIEW_KEY,
        fingerprint,
        items,
        summary=summary,
        source_event_count=(
            len(cleanup_events)
            + len(import_events)
            + len(library_artifacts)
            + len(traces)
        ),
    )
    return {
        "items": items,
        "summary": summary,
        "projection": _metadata(db.projection_snapshot(CLEANUP_REVIEW_KEY), fingerprint),
    }


def cleanup_review_projection(config: Config) -> dict[str, Any]:
    fingerprint = cleanup_review_fingerprint(config)
    snapshot = db.projection_snapshot(CLEANUP_REVIEW_KEY)
    items = snapshot.get("payload") if snapshot else []
    if not isinstance(items, list):
        items = []
    summary = snapshot.get("summary") if snapshot else {}
    if not isinstance(summary, dict):
        summary = {}
    return {
        "items": items,
        "summary": summary,
        "projection": _metadata(snapshot, fingerprint),
    }


def cleanup_review_projection_summary(config: Config) -> dict[str, Any]:
    fingerprint = cleanup_review_fingerprint(config)
    snapshot = db.projection_snapshot_summary(CLEANUP_REVIEW_KEY)
    summary = snapshot.get("summary") if snapshot else {}
    if not isinstance(summary, dict):
        summary = {}
    return {
        "summary": summary,
        "projection": _metadata(snapshot, fingerprint),
    }


def rebuild_library_enriched_projection(config: Config) -> dict[str, Any]:
    fingerprint = library_enriched_fingerprint(config)
    snapshot = db.projection_snapshot(LIBRARY_ENRICHED_KEY)
    if snapshot and snapshot.get("fingerprint") == fingerprint:
        artifacts = snapshot.get("payload") if isinstance(snapshot.get("payload"), list) else []
        summary = snapshot.get("summary") if isinstance(snapshot.get("summary"), dict) else {}
        return {
            "artifacts": artifacts,
            "summary": summary,
            "projection": _metadata(snapshot, fingerprint),
        }

    artifacts = db.all_library_artifacts()
    enriched = enrich_library_artifacts(artifacts, config)
    summary = summarize_library(enriched)
    db.upsert_projection_snapshot(
        LIBRARY_ENRICHED_KEY,
        fingerprint,
        enriched,
        summary=summary,
        source_event_count=len(artifacts),
    )
    return {
        "artifacts": enriched,
        "summary": summary,
        "projection": _metadata(db.projection_snapshot(LIBRARY_ENRICHED_KEY), fingerprint),
    }


def library_enriched_projection(config: Config) -> dict[str, Any]:
    fingerprint = library_enriched_fingerprint(config)
    snapshot = db.projection_snapshot(LIBRARY_ENRICHED_KEY)
    artifacts = snapshot.get("payload") if snapshot else []
    if not isinstance(artifacts, list):
        artifacts = []
    summary = snapshot.get("summary") if snapshot else {}
    if not isinstance(summary, dict):
        summary = {}
    return {
        "artifacts": artifacts,
        "summary": summary,
        "projection": _metadata(snapshot, fingerprint),
    }
