"""Cached projections for expensive read-only views."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from . import db
from .cleanup_review import build_cleanup_review
from .config import Config
from .library import enrich_library_artifacts
from .perf import timed, trace


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
            "cleanup_execution": config.section("cleanup_execution"),
            "cleanup_review": config.section("cleanup_review"),
        },
    )


def cached_cleanup_review_items(config: Config) -> list[dict[str, Any]]:
    key = "cleanup_review:v1"
    with timed("projection_fingerprint", projection=key):
        fingerprint = cleanup_review_fingerprint(config)
    with timed("projection_snapshot_read", projection=key):
        snapshot = db.projection_snapshot(key)
    if snapshot and snapshot.get("fingerprint") == fingerprint and isinstance(snapshot.get("payload"), list):
        trace(
            "projection_cache",
            projection=key,
            cache="hit",
            items=len(snapshot["payload"]),
        )
        return snapshot["payload"]
    trace("projection_cache", projection=key, cache="miss")
    with timed("cleanup_review_generation", cache="miss"):
        items = build_cleanup_review(
            db.all_cleanup_events(),
            db.all_import_events(),
            db.all_library_artifacts(),
            db.all_traces(),
            config,
        )
    with timed("projection_snapshot_write", projection=key, items=len(items)):
        db.upsert_projection_snapshot(key, fingerprint, items)
    return items


def validation_fingerprint(config: Config) -> str:
    return _fingerprint(
        [
            db.table_fingerprint("import_events"),
            db.table_fingerprint("library_artifacts"),
            db.table_fingerprint("cleanup_events"),
            db.table_fingerprint("recommendations"),
            db.completed_cleanup_execution_fingerprint(),
            db.table_fingerprint("cleanup_execution_batches"),
            db.table_fingerprint("handoff_traces"),
            db.raw_event_fingerprint("cleanup", "file_evidence"),
        ],
        {
            "cleanup_execution": config.section("cleanup_execution"),
            "cleanup_review": config.section("cleanup_review"),
        },
    )


def cached_validation(config: Config, run: Any) -> dict[str, Any]:
    key = "validation:v1"
    with timed("projection_fingerprint", projection=key):
        fingerprint = validation_fingerprint(config)
    with timed("projection_snapshot_read", projection=key):
        snapshot = db.projection_snapshot(key)
    if snapshot and snapshot.get("fingerprint") == fingerprint and isinstance(snapshot.get("payload"), dict):
        trace(
            "projection_cache",
            projection=key,
            cache="hit",
            status=snapshot["payload"].get("status"),
            checks=len(snapshot["payload"].get("checks") or []),
        )
        return snapshot["payload"]
    trace("projection_cache", projection=key, cache="miss")
    with timed("validation_generation", cache="miss"):
        result = run(config)
    with timed("projection_snapshot_write", projection=key):
        db.upsert_projection_snapshot(key, fingerprint, result)
    return result


def cached_enriched_library_artifacts(config: Config) -> list[dict[str, Any]]:
    key = "validation_library_artifacts:v1"
    with timed("projection_fingerprint", projection=key):
        fingerprint = _fingerprint(
            [db.table_fingerprint("library_artifacts")],
            {"library": config.section("library")},
        )
    with timed("projection_snapshot_read", projection=key):
        snapshot = db.projection_snapshot(key)
    if snapshot and snapshot.get("fingerprint") == fingerprint and isinstance(snapshot.get("payload"), list):
        trace(
            "projection_cache",
            projection=key,
            cache="hit",
            artifacts=len(snapshot["payload"]),
        )
        return snapshot["payload"]
    trace("projection_cache", projection=key, cache="miss")
    with timed("library_enrichment_for_validation", cache="miss"):
        artifacts = enrich_library_artifacts(db.all_library_artifacts(), config)
    with timed("projection_snapshot_write", projection=key, artifacts=len(artifacts)):
        db.upsert_projection_snapshot(key, fingerprint, artifacts)
    return artifacts
