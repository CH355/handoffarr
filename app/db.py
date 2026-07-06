"""SQLite storage for Handoffarr.

Stores raw collector events and correlated handoff traces. The database lives at
/data/handoffarr.sqlite3 by default and is created on first use.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import threading
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("handoffarr.db")
dedup_audit_logger = logging.getLogger("handoffarr.audit.raw_event_dedup")

DB_PATH = os.environ.get("HANDOFFARR_DB", "/data/handoffarr.sqlite3")

_lock = threading.Lock()
_audit_lock = threading.Lock()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they do not exist."""
    with _lock, _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS raw_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                event_type TEXT,
                external_id TEXT,
                title TEXT,
                torrent_hash TEXT,
                download_id TEXT,
                payload_json TEXT,
                payload_fingerprint TEXT,
                observed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS handoff_traces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                seerr_request_id TEXT,
                seerr_status TEXT,
                radarr_history_id TEXT,
                torrent_hash TEXT,
                download_id TEXT,
                selected_release TEXT,
                reported_seeds INTEGER,
                reported_indexer TEXT,
                qbittorrent_state TEXT,
                actual_seeds INTEGER,
                actual_peers INTEGER,
                dlspeed INTEGER,
                diagnosis TEXT,
                updated_at TEXT,
                match_source TEXT,
                match_confidence REAL,
                match_reasons TEXT,
                normalized_title TEXT,
                state_classification TEXT
            );

            CREATE TABLE IF NOT EXISTS import_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_id TEXT,
                source_application TEXT,
                media_type TEXT,
                media_id TEXT,
                media_title TEXT,
                source_path TEXT,
                destination_path TEXT,
                import_status TEXT,
                import_timestamp TEXT,
                evidence_json TEXT
            );

            CREATE TABLE IF NOT EXISTS library_artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artifact_id TEXT,
                media_id TEXT,
                media_title TEXT,
                media_type TEXT,
                library_path TEXT,
                file_exists INTEGER,
                file_size INTEGER,
                source_application TEXT,
                observed_at TEXT,
                evidence_json TEXT
            );

            CREATE TABLE IF NOT EXISTS cleanup_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cleanup_id TEXT,
                media_id TEXT,
                media_title TEXT,
                source_application TEXT,
                torrent_hash TEXT,
                cleanup_status TEXT,
                retained_bytes INTEGER,
                cleanup_timestamp TEXT,
                evidence_json TEXT
            );

            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recommendation_id TEXT,
                priority TEXT,
                category TEXT,
                title TEXT,
                summary TEXT,
                recommended_action TEXT,
                expected_impact_json TEXT,
                confidence TEXT,
                evidence_json TEXT,
                related_assessment_id TEXT,
                observed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS timeline_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timeline_id TEXT,
                media_id TEXT,
                media_title TEXT,
                stage TEXT,
                stage_status TEXT,
                source TEXT,
                timestamp TEXT,
                evidence_json TEXT
            );

            CREATE TABLE IF NOT EXISTS decision_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id TEXT,
                media_id TEXT,
                media_title TEXT,
                selected_release TEXT,
                source_application TEXT,
                source_indexer TEXT,
                candidate_count INTEGER,
                decision_reason TEXT,
                decision_quality TEXT,
                confidence TEXT,
                evidence_json TEXT,
                observed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS responsibility_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assessment_id TEXT,
                lifecycle_stage TEXT,
                diagnosis TEXT,
                responsible_domain TEXT,
                confidence TEXT,
                evidence_json TEXT,
                impact_json TEXT,
                recommended_action TEXT,
                observed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS cleanup_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT,
                batch_id TEXT,
                media_id TEXT,
                media_title TEXT,
                qbit_hash TEXT,
                review_class TEXT,
                match_strength TEXT,
                requested_action TEXT,
                execution_status TEXT,
                recoverable_bytes INTEGER,
                confirmation_phrase TEXT,
                blocking_reasons_json TEXT,
                evidence_json TEXT,
                created_at TEXT,
                completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS cleanup_execution_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT,
                status TEXT,
                item_count INTEGER,
                completed_count INTEGER,
                failed_count INTEGER,
                planned_recoverable_bytes INTEGER,
                actual_recovered_bytes INTEGER,
                created_at TEXT,
                completed_at TEXT,
                evidence_json TEXT
            );

            CREATE TABLE IF NOT EXISTS projection_snapshots (
                projection_key TEXT PRIMARY KEY,
                fingerprint TEXT,
                payload_json TEXT,
                summary_json TEXT,
                source_event_count INTEGER,
                generated_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS qbittorrent_torrents (
                torrent_hash TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                observed_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS recovery_agent_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                enabled INTEGER NOT NULL,
                interval_minutes INTEGER NOT NULL,
                agent_status TEXT NOT NULL,
                last_evaluation_at TEXT,
                next_evaluation_at TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS recovery_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE NOT NULL,
                torrent_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                error TEXT
            );

            CREATE TABLE IF NOT EXISTS recovery_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id TEXT UNIQUE NOT NULL,
                job_id TEXT,
                torrent_hash TEXT NOT NULL,
                media_id TEXT,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                current_health_json TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                confidence REAL NOT NULL,
                reasoning_json TEXT NOT NULL,
                replacement_candidates_json TEXT NOT NULL,
                planned_action TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS recovery_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                history_id TEXT UNIQUE NOT NULL,
                job_id TEXT,
                plan_id TEXT,
                timestamp TEXT NOT NULL,
                torrent_hash TEXT NOT NULL,
                health_json TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                confidence REAL NOT NULL,
                selected_candidate_json TEXT,
                evaluation_duration_ms REAL NOT NULL,
                candidate_count INTEGER NOT NULL,
                decision TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_raw_events_source
                ON raw_events (source, observed_at);
            CREATE INDEX IF NOT EXISTS idx_raw_events_source_type
                ON raw_events (source, event_type, observed_at);
            CREATE INDEX IF NOT EXISTS idx_raw_events_hash
                ON raw_events (torrent_hash);
            CREATE INDEX IF NOT EXISTS idx_raw_events_identity_external
                ON raw_events (source, event_type, external_id, id);
            CREATE INDEX IF NOT EXISTS idx_responsibility_assessments_domain
                ON responsibility_assessments (responsible_domain, observed_at);
            CREATE INDEX IF NOT EXISTS idx_import_events_media
                ON import_events (media_id, import_timestamp);
            CREATE INDEX IF NOT EXISTS idx_import_events_status
                ON import_events (import_status, import_timestamp);
            CREATE INDEX IF NOT EXISTS idx_library_artifacts_media
                ON library_artifacts (media_id, observed_at);
            CREATE INDEX IF NOT EXISTS idx_library_artifacts_path
                ON library_artifacts (library_path);
            CREATE INDEX IF NOT EXISTS idx_cleanup_events_media
                ON cleanup_events (media_id, cleanup_timestamp);
            CREATE INDEX IF NOT EXISTS idx_cleanup_events_status
                ON cleanup_events (cleanup_status, cleanup_timestamp);
            CREATE INDEX IF NOT EXISTS idx_timeline_events_media
                ON timeline_events (media_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_timeline_events_timeline
                ON timeline_events (timeline_id, stage);
            CREATE INDEX IF NOT EXISTS idx_decision_assessments_media
                ON decision_assessments (media_id, observed_at);
            CREATE INDEX IF NOT EXISTS idx_decision_assessments_quality
                ON decision_assessments (decision_quality, observed_at);
            CREATE INDEX IF NOT EXISTS idx_recommendations_priority
                ON recommendations (priority, observed_at);
            CREATE INDEX IF NOT EXISTS idx_recommendations_category
                ON recommendations (category, observed_at);
            CREATE INDEX IF NOT EXISTS idx_cleanup_executions_created
                ON cleanup_executions (created_at);
            CREATE INDEX IF NOT EXISTS idx_cleanup_executions_media
                ON cleanup_executions (media_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_cleanup_execution_batches_batch
                ON cleanup_execution_batches (batch_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_recovery_jobs_created
                ON recovery_jobs (created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_recovery_jobs_status
                ON recovery_jobs (status, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_recovery_plans_torrent
                ON recovery_plans (torrent_hash, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_recovery_history_timestamp
                ON recovery_history (timestamp DESC);
            """
        )
        _migrate_handoff_traces(conn)
        _migrate_cleanup_executions(conn)
        _migrate_projection_snapshots(conn)
        _migrate_raw_events_dedup(conn)
    logger.info("Database initialized at %s", DB_PATH)


# Correlation-diagnostic columns added after the original schema shipped. Stored
# as (column, SQLite type) so we can ALTER existing databases in place rather
# than dropping the table and losing trace history.
_TRACE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("match_source", "TEXT"),
    ("match_confidence", "REAL"),
    ("match_reasons", "TEXT"),
    ("normalized_title", "TEXT"),
    ("state_classification", "TEXT"),
    ("seerr_status", "TEXT"),
    ("dlspeed", "INTEGER"),
    ("import_status", "TEXT"),
    ("imported_by", "TEXT"),
    ("import_timestamp", "TEXT"),
    ("library_status", "TEXT"),
    ("library_path", "TEXT"),
    ("library_size", "INTEGER"),
    ("potential_cleanup_candidate", "INTEGER"),
    ("cleanup_status", "TEXT"),
    ("retained_bytes", "INTEGER"),
    ("recoverable_bytes", "INTEGER"),
)


def _migrate_handoff_traces(conn: sqlite3.Connection) -> None:
    """Add any missing diagnostic columns to an existing handoff_traces table.

    CREATE TABLE above already includes these for fresh databases; this brings
    pre-existing databases up to the same shape without a migrations framework.
    """
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(handoff_traces)")}
    for name, col_type in _TRACE_COLUMNS:
        if name not in existing:
            conn.execute(f"ALTER TABLE handoff_traces ADD COLUMN {name} {col_type}")
            logger.info("Migrated handoff_traces: added column %s", name)


_CLEANUP_EXECUTION_COLUMNS: tuple[tuple[str, str], ...] = (
    ("batch_id", "TEXT"),
)


def _migrate_cleanup_executions(conn: sqlite3.Connection) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(cleanup_executions)")}
    for name, col_type in _CLEANUP_EXECUTION_COLUMNS:
        if name not in existing:
            conn.execute(f"ALTER TABLE cleanup_executions ADD COLUMN {name} {col_type}")
            logger.info("Migrated cleanup_executions: added column %s", name)
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_cleanup_executions_batch
            ON cleanup_executions (batch_id, created_at)
        """
    )


_PROJECTION_SNAPSHOT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("fingerprint", "TEXT"),
    ("payload_json", "TEXT"),
    ("summary_json", "TEXT"),
    ("source_event_count", "INTEGER"),
    ("generated_at", "TEXT"),
    ("updated_at", "TEXT"),
)


def _migrate_projection_snapshots(conn: sqlite3.Connection) -> None:
    existing = {
        row["name"] for row in conn.execute("PRAGMA table_info(projection_snapshots)")
    }
    for name, col_type in _PROJECTION_SNAPSHOT_COLUMNS:
        if name not in existing:
            conn.execute(f"ALTER TABLE projection_snapshots ADD COLUMN {name} {col_type}")
            logger.info("Migrated projection_snapshots: added column %s", name)

    refreshed = {
        row["name"] for row in conn.execute("PRAGMA table_info(projection_snapshots)")
    }
    if "generated_at" in refreshed:
        if "created_at" in refreshed and "updated_at" in refreshed:
            conn.execute(
                """
                UPDATE projection_snapshots
                SET generated_at = COALESCE(generated_at, created_at, updated_at)
                WHERE generated_at IS NULL
                """
            )
        elif "updated_at" in refreshed:
            conn.execute(
                """
                UPDATE projection_snapshots
                SET generated_at = COALESCE(generated_at, updated_at)
                WHERE generated_at IS NULL
                """
            )


_DEDUP_RAW_EVENT_TYPES: frozenset[tuple[str, str]] = frozenset(
    {
        ("qbittorrent", "torrent"),
        ("cleanup", "observation"),
        ("cleanup", "file_evidence"),
        ("decision", "observation"),
        ("library", "artifact"),
        ("lidarr", "import_success"),
        ("radarr", "downloadfolderimported"),
        ("radarr", "grabbed"),
        ("radarr", "import_success"),
        ("seerr", "request"),
        ("sonarr", "import_success"),
    }
)

_RAW_EVENT_DEDUP_COLUMNS: tuple[tuple[str, str], ...] = (
    ("payload_fingerprint", "TEXT"),
)

_VOLATILE_FINGERPRINT_KEYS: frozenset[str] = frozenset(
    {
        "age",
        "last_seen",
        "observed_at",
        "relative_time",
        "timestamp",
        "updated_at",
         "age",
        "availability",
        "import_timestamp",
        "last_seen",
        "num_leechs",
        "num_seeds",
        "observed_at",
        "ratio",
        "relative_time",
        "seeding_time",
        "timestamp",
        "updated_at",
   }
)

_DEDUP_AUDIT_SAMPLE_LIMIT = 10
_DEDUP_AUDIT_VALUE_LIMIT = 240
_DEDUP_AUDIT_LIST_PREVIEW = 3
_DEDUP_AUDIT_DEEP_DIFF_LIMIT = 40
_QBITTORRENT_TORRENT_VOLATILE_FINGERPRINT_KEYS: frozenset[str] = frozenset(
    {
        "peers",
        "seeds",
        "tracker",
        "uploaded",
    }
)
_DEDUP_AUDIT: dict[str, dict[str, Any]] = {}


def _migrate_raw_events_dedup(conn: sqlite3.Connection) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(raw_events)")}
    for name, col_type in _RAW_EVENT_DEDUP_COLUMNS:
        if name not in existing:
            conn.execute(f"ALTER TABLE raw_events ADD COLUMN {name} {col_type}")
            logger.info("Migrated raw_events: added column %s", name)
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_raw_events_identity_external
            ON raw_events (source, event_type, external_id, id)
        """
    )


def _fingerprint_payload(
    value: Any,
    volatile_keys: frozenset[str] = _VOLATILE_FINGERPRINT_KEYS,
) -> Any:
    if isinstance(value, dict):
        return {
            str(k): _fingerprint_payload(v, volatile_keys)
            for k, v in value.items()
            if str(k) not in volatile_keys
        }
    if isinstance(value, list):
        return [_fingerprint_payload(item, volatile_keys) for item in value]
    return value


def _fingerprint_payload_for_event(source: str, event_type: str, value: Any) -> Any:
    volatile_keys = _VOLATILE_FINGERPRINT_KEYS
    if source == "qbittorrent" and event_type == "torrent":
        volatile_keys = volatile_keys | _QBITTORRENT_TORRENT_VOLATILE_FINGERPRINT_KEYS
    return _fingerprint_payload(value, volatile_keys)


def _recompute_latest_fingerprint(source: str, event_type: str) -> bool:
    return source == "qbittorrent" and event_type == "torrent"


def _dedup_audit_key(source: str, event_type: str) -> str:
    return f"{source}/{event_type}"


def _dedup_audit_bucket(source: str, event_type: str) -> dict[str, Any]:
    key = _dedup_audit_key(source, event_type)
    bucket = _DEDUP_AUDIT.get(key)
    if bucket is None:
        bucket = {
            "source": source,
            "event_type": event_type,
            "attempted": 0,
            "inserted": 0,
            "suppressed_as_duplicate": 0,
            "inserted_with_prior_row": 0,
            "inserted_without_prior_row": 0,
            "logged_diff_samples": 0,
            "diff_samples": [],
        }
        _DEDUP_AUDIT[key] = bucket
    return bucket


def _summarize_audit_value(value: Any) -> Any:
    if isinstance(value, str):
        if len(value) > _DEDUP_AUDIT_VALUE_LIMIT:
            return {
                "type": "str",
                "length": len(value),
                "preview": value[:_DEDUP_AUDIT_VALUE_LIMIT],
                "truncated": True,
            }
        return value
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        keys = sorted(str(k) for k in value.keys())
        preview: dict[str, Any] = {}
        for key in keys[:_DEDUP_AUDIT_LIST_PREVIEW]:
            preview[key] = _summarize_audit_value(value.get(key))
        return {
            "type": "dict",
            "keys": keys[:20],
            "key_count": len(keys),
            "preview": preview,
        }
    if isinstance(value, list):
        return {
            "type": "list",
            "length": len(value),
            "preview": [
                _summarize_audit_value(item)
                for item in value[:_DEDUP_AUDIT_LIST_PREVIEW]
            ],
        }
    return repr(value)[:_DEDUP_AUDIT_VALUE_LIMIT]


def _summarize_changed_branch(old: Any, new: Any) -> dict[str, Any]:
    if isinstance(old, dict) and isinstance(new, dict):
        old_keys = set(old.keys())
        new_keys = set(new.keys())
        changed = sorted(k for k in old_keys & new_keys if old.get(k) != new.get(k))
        return {
            "old": _summarize_audit_value(old),
            "new": _summarize_audit_value(new),
            "added_keys": sorted(new_keys - old_keys)[:20],
            "removed_keys": sorted(old_keys - new_keys)[:20],
            "changed_keys": changed[:20],
            "changed_key_count": len(changed),
        }
    if isinstance(old, list) and isinstance(new, list):
        changed_indexes: list[int] = []
        for idx, (old_item, new_item) in enumerate(zip(old, new)):
            if old_item != new_item:
                changed_indexes.append(idx)
            if len(changed_indexes) >= 20:
                break
        return {
            "old": _summarize_audit_value(old),
            "new": _summarize_audit_value(new),
            "old_length": len(old),
            "new_length": len(new),
            "changed_indexes": changed_indexes,
            "length_changed": len(old) != len(new),
        }
    return {
        "old": _summarize_audit_value(old),
        "new": _summarize_audit_value(new),
    }


def _payload_diff_summary(old: Any, new: Any) -> tuple[list[str], dict[str, Any]]:
    if not isinstance(old, dict) or not isinstance(new, dict):
        return ["$"], {"$": _summarize_changed_branch(old, new)}
    old_keys = set(old.keys())
    new_keys = set(new.keys())
    changed_keys = sorted(
        (old_keys ^ new_keys) | {k for k in old_keys & new_keys if old.get(k) != new.get(k)}
    )
    changes = {
        key: _summarize_changed_branch(old.get(key), new.get(key))
        for key in changed_keys[:30]
    }
    return changed_keys, changes
def _append_deep_diff(
    *,
    path: str,
    old: Any,
    new: Any,
    output: list[dict[str, Any]],
    limit: int,
) -> None:
    if len(output) >= limit:
        return

    if type(old) is not type(new):
        output.append(
            {
                "path": path,
                "old": _summarize_audit_value(old),
                "new": _summarize_audit_value(new),
                "reason": "type_changed",
            }
        )
        return

    if isinstance(old, dict):
        old_keys = set(old.keys())
        new_keys = set(new.keys())

        for key in sorted(old_keys - new_keys):
            if len(output) >= limit:
                return
            output.append(
                {
                    "path": f"{path}.{key}" if path != "$" else f"$.{key}",
                    "old": _summarize_audit_value(old.get(key)),
                    "new": None,
                    "reason": "removed",
                }
            )

        for key in sorted(new_keys - old_keys):
            if len(output) >= limit:
                return
            output.append(
                {
                    "path": f"{path}.{key}" if path != "$" else f"$.{key}",
                    "old": None,
                    "new": _summarize_audit_value(new.get(key)),
                    "reason": "added",
                }
            )

        for key in sorted(old_keys & new_keys):
            if len(output) >= limit:
                return
            old_value = old.get(key)
            new_value = new.get(key)
            if old_value != new_value:
                child_path = f"{path}.{key}" if path != "$" else f"$.{key}"
                _append_deep_diff(
                    path=child_path,
                    old=old_value,
                    new=new_value,
                    output=output,
                    limit=limit,
                )
        return

    if isinstance(old, list):
        min_len = min(len(old), len(new))
        for idx in range(min_len):
            if len(output) >= limit:
                return
            if old[idx] != new[idx]:
                _append_deep_diff(
                    path=f"{path}[{idx}]",
                    old=old[idx],
                    new=new[idx],
                    output=output,
                    limit=limit,
                )

        if len(old) != len(new) and len(output) < limit:
            output.append(
                {
                    "path": path,
                    "old_length": len(old),
                    "new_length": len(new),
                    "old": _summarize_audit_value(old),
                    "new": _summarize_audit_value(new),
                    "reason": "list_length_changed",
                }
            )
        return

    output.append(
        {
            "path": path,
            "old": _summarize_audit_value(old),
            "new": _summarize_audit_value(new),
            "reason": "value_changed",
        }
    )


def _payload_deep_diff(old: Any, new: Any) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    _append_deep_diff(
        path="$",
        old=old,
        new=new,
        output=output,
        limit=_DEDUP_AUDIT_DEEP_DIFF_LIMIT,
    )
    return output

def _dedup_audit_attempt(source: str, event_type: str) -> None:
    with _audit_lock:
        _dedup_audit_bucket(source, event_type)["attempted"] += 1


def _dedup_audit_suppressed(source: str, event_type: str) -> None:
    with _audit_lock:
        bucket = _dedup_audit_bucket(source, event_type)
        bucket["suppressed_as_duplicate"] += 1


def _dedup_audit_inserted(
    *,
    source: str,
    event_type: str,
    identity: tuple[str, str],
    previous_row: sqlite3.Row | None,
    previous_normalized_payload: Any,
    new_normalized_payload: Any,
    new_observed_at: str,
    previous_had_fingerprint: bool,
    fingerprint_changed: bool,
) -> None:
    sample: dict[str, Any] | None = None
    with _audit_lock:
        bucket = _dedup_audit_bucket(source, event_type)
        bucket["inserted"] += 1
        if previous_row is None:
            bucket["inserted_without_prior_row"] += 1
            return
        bucket["inserted_with_prior_row"] += 1
        if bucket["logged_diff_samples"] >= _DEDUP_AUDIT_SAMPLE_LIMIT:
            return
        changed_keys, changes = _payload_diff_summary(
            previous_normalized_payload,
            new_normalized_payload,
        )
        deep_diff = _payload_deep_diff(
            previous_normalized_payload,
            new_normalized_payload,
        )
        sample = {
            "source": source,
            "event_type": event_type,
            "identity": {"kind": identity[0], "value": identity[1]},
            "previous_row_id": previous_row["id"],
            "new_event_candidate_timestamp": new_observed_at,
            "previous_had_payload_fingerprint": previous_had_fingerprint,
            "fingerprint_changed": fingerprint_changed,
            "changed_keys": changed_keys[:30],
            "changed_key_count": len(changed_keys),
            "changes": changes,
            "deep_diff": deep_diff,
        }
        bucket["diff_samples"].append(sample)
        bucket["logged_diff_samples"] += 1
    if sample is not None:
        dedup_audit_logger.info(json.dumps(sample, sort_keys=True, default=str))


def raw_event_dedup_audit_snapshot() -> dict[str, Any]:
    with _audit_lock:
        return {
            "sample_limit_per_event_type": _DEDUP_AUDIT_SAMPLE_LIMIT,
            "event_types": deepcopy(_DEDUP_AUDIT),
        }


def _raw_event_identity(
    source: str,
    event_type: str,
    external_id: str | None,
    torrent_hash: str | None,
    download_id: str | None,
) -> tuple[str, str] | None:
    if source == "cleanup" and event_type == "file_evidence" and torrent_hash:
        return ("torrent_hash", torrent_hash.lower())
    if external_id:
        return ("external_id", str(external_id))
    if torrent_hash:
        return ("torrent_hash", torrent_hash.lower())
    return None


def _raw_event_fingerprint(
    *,
    source: str,
    event_type: str,
    identity: tuple[str, str],
    payload: Any,
) -> str:
    body = {
        "source": source,
        "event_type": event_type,
        "identity": identity,
        "payload": _fingerprint_payload_for_event(source, event_type, payload),
    }
    encoded = json.dumps(body, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _fingerprint_from_payload_json(
    *,
    source: str,
    event_type: str,
    identity: tuple[str, str],
    payload_json: str | None,
) -> str | None:
    payload = _normalized_payload_from_json(
        payload_json,
        source=source,
        event_type=event_type,
    )
    if payload is None:
        return None
    return _raw_event_fingerprint(
        source=source,
        event_type=event_type,
        identity=identity,
        payload=payload,
    )


def _normalized_payload_from_json(
    payload_json: str | None,
    *,
    source: str,
    event_type: str,
) -> Any:
    if not payload_json:
        return None
    try:
        return _fingerprint_payload_for_event(source, event_type, json.loads(payload_json))
    except (TypeError, ValueError):
        return None


def _latest_raw_event_for_identity(
    conn: sqlite3.Connection,
    *,
    source: str,
    event_type: str,
    identity: tuple[str, str],
) -> sqlite3.Row | None:
    field, value = identity
    if field not in {"external_id", "torrent_hash"}:
        return None
    return conn.execute(
        f"""
        SELECT id, payload_fingerprint, payload_json
        FROM raw_events
        WHERE source = ? AND event_type = ? AND {field} = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (source, event_type, value),
    ).fetchone()


def insert_raw_event(
    *,
    source: str,
    event_type: str,
    external_id: str | None,
    title: str | None,
    torrent_hash: str | None,
    download_id: str | None,
    payload: Any,
    observed_at: str | None = None,
) -> bool:
    normalized_external_id = str(external_id) if external_id is not None else None
    normalized_torrent_hash = torrent_hash.lower() if torrent_hash else None
    normalized_download_id = str(download_id) if download_id is not None else None
    payload_json = json.dumps(payload, default=str)
    new_observed_at = observed_at or _utcnow()
    identity = _raw_event_identity(
        source,
        event_type,
        normalized_external_id,
        normalized_torrent_hash,
        normalized_download_id,
    )
    payload_fingerprint = (
        _raw_event_fingerprint(
            source=source,
            event_type=event_type,
            identity=identity,
            payload=payload,
        )
        if identity
        else None
    )
    dedup_covered = bool(
        (source, event_type) in _DEDUP_RAW_EVENT_TYPES
        and identity
        and payload_fingerprint
    )
    latest: sqlite3.Row | None = None
    latest_fingerprint: str | None = None
    previous_had_fingerprint = False
    previous_normalized_payload: Any = None
    new_normalized_payload = _fingerprint_payload_for_event(source, event_type, payload)
    if dedup_covered:
        _dedup_audit_attempt(source, event_type)
    with _lock, _connect() as conn:
        if dedup_covered:
            latest = _latest_raw_event_for_identity(
                conn,
                source=source,
                event_type=event_type,
                identity=identity,
            )
            if latest:
                latest_fingerprint = latest["payload_fingerprint"]
                previous_had_fingerprint = latest_fingerprint is not None
                previous_normalized_payload = _normalized_payload_from_json(
                    latest["payload_json"],
                    source=source,
                    event_type=event_type,
                )
                if latest_fingerprint is None or _recompute_latest_fingerprint(
                    source,
                    event_type,
                ):
                    latest_fingerprint = _fingerprint_from_payload_json(
                        source=source,
                        event_type=event_type,
                        identity=identity,
                        payload_json=latest["payload_json"],
                    )
                if latest_fingerprint == payload_fingerprint:
                    _dedup_audit_suppressed(source, event_type)
                    return False
        conn.execute(
            """
            INSERT INTO raw_events
                (source, event_type, external_id, title, torrent_hash,
                 download_id, payload_json, payload_fingerprint, observed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source,
                event_type,
                normalized_external_id,
                title,
                normalized_torrent_hash,
                normalized_download_id,
                payload_json,
                payload_fingerprint,
                new_observed_at,
            ),
        )
    if dedup_covered and identity:
        _dedup_audit_inserted(
            source=source,
            event_type=event_type,
            identity=identity,
            previous_row=latest,
            previous_normalized_payload=previous_normalized_payload,
            new_normalized_payload=new_normalized_payload,
            new_observed_at=new_observed_at,
            previous_had_fingerprint=previous_had_fingerprint,
            fingerprint_changed=latest_fingerprint != payload_fingerprint,
        )
    return True


def recent_events(source: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    with _lock, _connect() as conn:
        if source:
            rows = conn.execute(
                "SELECT * FROM raw_events WHERE source = ? "
                "ORDER BY id DESC LIMIT ?",
                (source, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM raw_events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]


def events_for_torrent(torrent_hash: str, limit: int = 200) -> list[dict[str, Any]]:
    """Return stored Arr evidence for one torrent without a time-window cutoff."""
    target = str(torrent_hash or "").strip().lower()
    if not target:
        return []
    with _lock, _connect() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM raw_events
            WHERE source IN ('radarr', 'sonarr')
              AND (
                lower(COALESCE(torrent_hash, '')) = ?
                OR lower(COALESCE(download_id, '')) = ?
              )
            ORDER BY id DESC
            LIMIT ?
            """,
            (target, target, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def events_for_source_since(source: str, since_iso: str) -> list[dict[str, Any]]:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM raw_events WHERE source = ? AND observed_at >= ? "
            "ORDER BY id DESC",
            (source, since_iso),
        ).fetchall()
    return [dict(r) for r in rows]


def latest_events_for_source_since_by_hash(source: str, since_iso: str) -> list[dict[str, Any]]:
    """Return latest raw event per torrent hash, preserving id fallback semantics."""
    with _lock, _connect() as conn:
        rows = conn.execute(
            """
            SELECT r.*
            FROM raw_events r
            JOIN (
                SELECT
                    CASE
                        WHEN torrent_hash IS NULL OR torrent_hash = '' THEN 'id:' || id
                        ELSE 'hash:' || lower(torrent_hash)
                    END AS dedupe_key,
                    MAX(id) AS max_id
                FROM raw_events
                WHERE source = ? AND observed_at >= ?
                GROUP BY dedupe_key
            ) latest ON latest.max_id = r.id
            ORDER BY r.id DESC
            """,
            (source, since_iso),
        ).fetchall()
    return [dict(r) for r in rows]


def replace_qbittorrent_torrents(torrents: list[dict[str, Any]]) -> None:
    """Atomically replace the current qBittorrent snapshot."""
    observed_at = _utcnow()
    with _lock, _connect() as conn:
        previous = {
            row["torrent_hash"]: json.loads(row["payload_json"])
            for row in conn.execute(
                "SELECT torrent_hash, payload_json FROM qbittorrent_torrents"
            ).fetchall()
        }
        conn.execute("DELETE FROM qbittorrent_torrents")
        rows: list[tuple[str, str, str]] = []
        for torrent in torrents:
            torrent_hash = str(torrent.get("hash") or "").strip().lower()
            if not torrent_hash:
                continue
            payload = dict(torrent)
            prior = previous.get(torrent_hash, {})
            if payload.get("dead_torrent"):
                payload["dead_since"] = (
                    prior.get("dead_since") if prior.get("dead_torrent") else observed_at
                )
            else:
                payload["dead_since"] = None
            rows.append(
                (torrent_hash, json.dumps(payload, default=str), observed_at)
            )
        conn.executemany(
            """
            INSERT INTO qbittorrent_torrents
                (torrent_hash, payload_json, observed_at)
            VALUES (?, ?, ?)
            """,
            rows,
        )


def all_qbittorrent_torrents() -> list[dict[str, Any]]:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT payload_json, observed_at FROM qbittorrent_torrents "
            "ORDER BY observed_at DESC, torrent_hash"
        ).fetchall()
    torrents = []
    for row in rows:
        payload = json.loads(row["payload_json"])
        payload["observed_at"] = row["observed_at"]
        torrents.append(payload)
    return torrents


def remove_qbittorrent_torrents(torrent_hashes: list[str]) -> None:
    hashes = [
        str(value).strip().lower()
        for value in torrent_hashes
        if str(value).strip()
    ]
    if not hashes:
        return
    placeholders = ",".join("?" for _ in hashes)
    with _lock, _connect() as conn:
        conn.execute(
            f"DELETE FROM qbittorrent_torrents "
            f"WHERE torrent_hash IN ({placeholders})",
            hashes,
        )


def recovery_agent_settings(
    *, default_enabled: bool = True, default_interval: int = 15
) -> dict[str, Any]:
    now = _utcnow()
    with _lock, _connect() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO recovery_agent_settings
                (id, enabled, interval_minutes, agent_status, updated_at)
            VALUES (1, ?, ?, 'Idle', ?)
            """,
            (1 if default_enabled else 0, default_interval, now),
        )
        row = conn.execute(
            "SELECT * FROM recovery_agent_settings WHERE id = 1"
        ).fetchone()
    result = dict(row) if row else {}
    result["enabled"] = bool(result.get("enabled"))
    return result


def update_recovery_agent_settings(**values: Any) -> dict[str, Any]:
    allowed = {
        "enabled",
        "interval_minutes",
        "agent_status",
        "last_evaluation_at",
        "next_evaluation_at",
    }
    updates = {key: value for key, value in values.items() if key in allowed}
    if not updates:
        return recovery_agent_settings()
    if "enabled" in updates:
        updates["enabled"] = 1 if updates["enabled"] else 0
    updates["updated_at"] = _utcnow()
    assignments = ", ".join(f"{key} = ?" for key in updates)
    with _lock, _connect() as conn:
        conn.execute(
            f"UPDATE recovery_agent_settings SET {assignments} WHERE id = 1",
            tuple(updates.values()),
        )
    return recovery_agent_settings()


def insert_recovery_job(job: dict[str, Any]) -> None:
    with _lock, _connect() as conn:
        conn.execute(
            """
            INSERT INTO recovery_jobs
                (job_id, torrent_hash, status, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                job["job_id"],
                job["torrent_hash"],
                job["status"],
                job["created_at"],
            ),
        )


def update_recovery_job(job_id: str, **values: Any) -> None:
    allowed = {"status", "started_at", "completed_at", "error"}
    updates = {key: value for key, value in values.items() if key in allowed}
    if not updates:
        return
    assignments = ", ".join(f"{key} = ?" for key in updates)
    with _lock, _connect() as conn:
        conn.execute(
            f"UPDATE recovery_jobs SET {assignments} WHERE job_id = ?",
            (*updates.values(), job_id),
        )


def recovery_jobs(limit: int = 100) -> list[dict[str, Any]]:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM recovery_jobs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]


def insert_recovery_plan(plan: dict[str, Any]) -> None:
    with _lock, _connect() as conn:
        conn.execute(
            """
            INSERT INTO recovery_plans
                (plan_id, job_id, torrent_hash, media_id, created_at, status,
                 current_health_json, recommendation, confidence, reasoning_json,
                 replacement_candidates_json, planned_action)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plan["id"],
                plan.get("job_id"),
                plan["torrent_hash"],
                plan.get("media_id"),
                plan["created_at"],
                plan["status"],
                json.dumps(plan["current_health"], default=str),
                plan["recommendation"],
                plan["confidence"],
                json.dumps(plan["reasoning"], default=str),
                json.dumps(plan["replacement_candidates"], default=str),
                plan["planned_action"],
            ),
        )


def recovery_plans(limit: int = 100) -> list[dict[str, Any]]:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM recovery_plans ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    plans = []
    for row in rows:
        plan = dict(row)
        plan["id"] = plan.pop("plan_id")
        plan["current_health"] = json.loads(
            plan.pop("current_health_json") or "{}"
        )
        plan["reasoning"] = json.loads(plan.pop("reasoning_json") or "[]")
        plan["replacement_candidates"] = json.loads(
            plan.pop("replacement_candidates_json") or "[]"
        )
        plans.append(plan)
    return plans


def latest_recovery_plans_by_torrent() -> dict[str, dict[str, Any]]:
    plans = recovery_plans(limit=1000)
    return {
        str(plan["torrent_hash"]).lower(): plan
        for plan in reversed(plans)
    }


def insert_recovery_history(entry: dict[str, Any]) -> None:
    with _lock, _connect() as conn:
        conn.execute(
            """
            INSERT INTO recovery_history
                (history_id, job_id, plan_id, timestamp, torrent_hash,
                 health_json, recommendation, confidence,
                 selected_candidate_json, evaluation_duration_ms,
                 candidate_count, decision)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry["history_id"],
                entry.get("job_id"),
                entry.get("plan_id"),
                entry["timestamp"],
                entry["torrent_hash"],
                json.dumps(entry["health"], default=str),
                entry["recommendation"],
                entry["confidence"],
                json.dumps(entry.get("selected_candidate"), default=str)
                if entry.get("selected_candidate")
                else None,
                entry["evaluation_duration_ms"],
                entry["candidate_count"],
                entry["decision"],
            ),
        )


def recovery_history(limit: int = 100) -> list[dict[str, Any]]:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM recovery_history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    entries = []
    for row in rows:
        entry = dict(row)
        entry["health"] = json.loads(entry.pop("health_json") or "{}")
        raw_candidate = entry.pop("selected_candidate_json")
        entry["selected_candidate"] = (
            json.loads(raw_candidate) if raw_candidate else None
        )
        entries.append(entry)
    return entries


def replace_traces(traces: list[dict[str, Any]]) -> None:
    """Replace the full trace snapshot. Traces are derived state, so we rebuild
    them on each correlation pass rather than trying to upsert."""
    now = _utcnow()
    with _lock, _connect() as conn:
        conn.execute("DELETE FROM handoff_traces")
        for t in traces:
            reasons = t.get("match_reasons")
            conn.execute(
                """
                INSERT INTO handoff_traces
                    (title, seerr_request_id, seerr_status, radarr_history_id,
                     torrent_hash, download_id, selected_release, reported_seeds,
                     reported_indexer, qbittorrent_state, actual_seeds,
                     actual_peers, dlspeed, diagnosis, updated_at, match_source,
                     match_confidence, match_reasons, normalized_title,
                     state_classification, import_status, imported_by,
                     import_timestamp, library_status, library_path, library_size,
                     potential_cleanup_candidate, cleanup_status, retained_bytes,
                     recoverable_bytes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    t.get("title"),
                    t.get("seerr_request_id"),
                    str(t.get("seerr_status"))
                    if t.get("seerr_status") is not None
                    else None,
                    t.get("radarr_history_id"),
                    t.get("torrent_hash"),
                    t.get("download_id"),
                    t.get("selected_release"),
                    t.get("reported_seeds"),
                    t.get("reported_indexer"),
                    t.get("qbittorrent_state"),
                    t.get("actual_seeds"),
                    t.get("actual_peers"),
                    t.get("dlspeed"),
                    t.get("diagnosis"),
                    now,
                    t.get("match_source"),
                    t.get("match_confidence"),
                    json.dumps(reasons) if reasons is not None else None,
                    t.get("normalized_title"),
                    t.get("state_classification"),
                    t.get("import_status"),
                    t.get("imported_by"),
                    t.get("import_timestamp"),
                    t.get("library_status"),
                    t.get("library_path"),
                    t.get("library_size"),
                    1 if t.get("potential_cleanup_candidate") else 0,
                    t.get("cleanup_status"),
                    t.get("retained_bytes"),
                    t.get("recoverable_bytes"),
                ),
            )


def all_traces() -> list[dict[str, Any]]:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM handoff_traces ORDER BY updated_at DESC, id DESC"
        ).fetchall()
    traces: list[dict[str, Any]] = []
    for r in rows:
        trace = dict(r)
        # match_reasons is stored as a JSON array; decode it back to a list so
        # API consumers and templates see structured data, not a JSON string.
        raw_reasons = trace.get("match_reasons")
        if raw_reasons:
            try:
                trace["match_reasons"] = json.loads(raw_reasons)
            except (TypeError, ValueError):
                trace["match_reasons"] = [raw_reasons]
        else:
            trace["match_reasons"] = []
        if "potential_cleanup_candidate" in trace:
            trace["potential_cleanup_candidate"] = bool(
                trace.get("potential_cleanup_candidate")
            )
        traces.append(trace)
    return traces


def replace_cleanup_events(cleanup_events: list[dict[str, Any]]) -> None:
    """Replace the current cleanup visibility snapshot."""
    observed_default = _utcnow()
    with _lock, _connect() as conn:
        conn.execute("DELETE FROM cleanup_events")
        for event in cleanup_events:
            conn.execute(
                """
                INSERT INTO cleanup_events
                    (cleanup_id, media_id, media_title, source_application,
                     torrent_hash, cleanup_status, retained_bytes,
                     cleanup_timestamp, evidence_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.get("cleanup_id"),
                    str(event.get("media_id"))
                    if event.get("media_id") is not None
                    else None,
                    event.get("media_title"),
                    event.get("source_application"),
                    event.get("torrent_hash"),
                    event.get("cleanup_status"),
                    event.get("retained_bytes"),
                    event.get("cleanup_timestamp") or observed_default,
                    json.dumps(event.get("evidence") or {}, default=str),
                ),
            )


def all_cleanup_events(media_id: str | None = None) -> list[dict[str, Any]]:
    with _lock, _connect() as conn:
        if media_id is None:
            rows = conn.execute(
                "SELECT * FROM cleanup_events "
                "ORDER BY cleanup_timestamp DESC, id DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM cleanup_events WHERE media_id = ? "
                "ORDER BY cleanup_timestamp DESC, id DESC",
                (media_id,),
            ).fetchall()

    events: list[dict[str, Any]] = []
    for row in rows:
        event = dict(row)
        raw_evidence = event.pop("evidence_json", None)
        if raw_evidence:
            try:
                event["evidence"] = json.loads(raw_evidence)
            except (TypeError, ValueError):
                event["evidence"] = {}
        else:
            event["evidence"] = {}
        status = event.get("cleanup_status")
        retained = event.get("retained_bytes") or 0
        event["recoverable_bytes"] = (
            retained
            if status in {"Cleanup Pending", "Cleanup Failed"}
            else 0
        )
        events.append(event)
    return events


def replace_import_events(import_events: list[dict[str, Any]]) -> None:
    """Replace the current import visibility snapshot."""
    with _lock, _connect() as conn:
        conn.execute("DELETE FROM import_events")
        for event in import_events:
            conn.execute(
                """
                INSERT INTO import_events
                    (import_id, source_application, media_type, media_id,
                     media_title, source_path, destination_path, import_status,
                     import_timestamp, evidence_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.get("import_id"),
                    event.get("source_application"),
                    event.get("media_type"),
                    str(event.get("media_id"))
                    if event.get("media_id") is not None
                    else None,
                    event.get("media_title"),
                    event.get("source_path"),
                    event.get("destination_path"),
                    event.get("import_status"),
                    event.get("import_timestamp"),
                    json.dumps(event.get("evidence") or {}, default=str),
                ),
            )


def all_import_events(media_id: str | None = None) -> list[dict[str, Any]]:
    with _lock, _connect() as conn:
        if media_id is None:
            rows = conn.execute(
                "SELECT * FROM import_events ORDER BY import_timestamp DESC, id DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM import_events WHERE media_id = ? "
                "ORDER BY import_timestamp DESC, id DESC",
                (media_id,),
            ).fetchall()

    events: list[dict[str, Any]] = []
    for row in rows:
        event = dict(row)
        raw_evidence = event.pop("evidence_json", None)
        if raw_evidence:
            try:
                event["evidence"] = json.loads(raw_evidence)
            except (TypeError, ValueError):
                event["evidence"] = {}
        else:
            event["evidence"] = {}
        events.append(event)
    return events


def replace_library_artifacts(artifacts: list[dict[str, Any]]) -> None:
    """Replace the current library visibility snapshot."""
    observed_default = _utcnow()
    with _lock, _connect() as conn:
        conn.execute("DELETE FROM library_artifacts")
        for artifact in artifacts:
            conn.execute(
                """
                INSERT INTO library_artifacts
                    (artifact_id, media_id, media_title, media_type, library_path,
                     file_exists, file_size, source_application, observed_at,
                     evidence_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact.get("artifact_id"),
                    str(artifact.get("media_id"))
                    if artifact.get("media_id") is not None
                    else None,
                    artifact.get("media_title"),
                    artifact.get("media_type"),
                    artifact.get("library_path"),
                    1 if artifact.get("file_exists") else 0,
                    artifact.get("file_size"),
                    artifact.get("source_application"),
                    artifact.get("observed_at") or observed_default,
                    json.dumps(artifact.get("evidence") or {}, default=str),
                ),
            )


def all_library_artifacts(media_id: str | None = None) -> list[dict[str, Any]]:
    with _lock, _connect() as conn:
        if media_id is None:
            rows = conn.execute(
                "SELECT * FROM library_artifacts ORDER BY observed_at DESC, id DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM library_artifacts WHERE media_id = ? "
                "ORDER BY observed_at DESC, id DESC",
                (media_id,),
            ).fetchall()

    artifacts: list[dict[str, Any]] = []
    for row in rows:
        artifact = dict(row)
        artifact["file_exists"] = bool(artifact.get("file_exists"))
        raw_evidence = artifact.pop("evidence_json", None)
        if raw_evidence:
            try:
                artifact["evidence"] = json.loads(raw_evidence)
            except (TypeError, ValueError):
                artifact["evidence"] = {}
        else:
            artifact["evidence"] = {}
        artifacts.append(artifact)
    return artifacts


def replace_responsibility_assessments(assessments: list[dict[str, Any]]) -> None:
    """Replace the full responsibility snapshot.

    Responsibility assessments are derived state for the current operational
    picture, so they follow the same delete-and-insert pattern as handoff traces.
    """
    observed_default = _utcnow()
    with _lock, _connect() as conn:
        conn.execute("DELETE FROM responsibility_assessments")
        for assessment in assessments:
            conn.execute(
                """
                INSERT INTO responsibility_assessments
                    (assessment_id, lifecycle_stage, diagnosis, responsible_domain,
                     confidence, evidence_json, impact_json, recommended_action,
                     observed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    assessment.get("assessment_id"),
                    assessment.get("lifecycle_stage"),
                    assessment.get("diagnosis"),
                    assessment.get("responsible_domain"),
                    assessment.get("confidence"),
                    json.dumps(assessment.get("evidence") or []),
                    json.dumps(assessment.get("impact") or {}),
                    assessment.get("recommended_action"),
                    assessment.get("observed_at") or observed_default,
                ),
            )


def replace_recommendations(recommendations: list[dict[str, Any]]) -> None:
    """Replace the full recommendations snapshot.

    Recommendations are derived state for the current operational picture and
    follow the same delete-and-insert pattern as traces and responsibility
    assessments.
    """
    observed_default = _utcnow()
    with _lock, _connect() as conn:
        conn.execute("DELETE FROM recommendations")
        for rec in recommendations:
            conn.execute(
                """
                INSERT INTO recommendations
                    (recommendation_id, priority, category, title, summary,
                     recommended_action, expected_impact_json, confidence,
                     evidence_json, related_assessment_id, observed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rec.get("recommendation_id"),
                    rec.get("priority"),
                    rec.get("category"),
                    rec.get("title"),
                    rec.get("summary"),
                    rec.get("recommended_action"),
                    json.dumps(rec.get("expected_impact") or {}),
                    rec.get("confidence"),
                    json.dumps(rec.get("evidence") or {}),
                    rec.get("related_assessment_id"),
                    rec.get("observed_at") or observed_default,
                ),
            )


def all_recommendations() -> list[dict[str, Any]]:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM recommendations ORDER BY observed_at DESC, id ASC"
        ).fetchall()

    recommendations: list[dict[str, Any]] = []
    for row in rows:
        rec = dict(row)
        for stored_key, public_key, default in (
            ("expected_impact_json", "expected_impact", {}),
            ("evidence_json", "evidence", {}),
        ):
            raw = rec.pop(stored_key, None)
            if raw:
                try:
                    rec[public_key] = json.loads(raw)
                except (TypeError, ValueError):
                    rec[public_key] = default
            else:
                rec[public_key] = default
        recommendations.append(rec)
    return recommendations


def replace_timeline_events(events: list[dict[str, Any]]) -> None:
    """Replace the current TimelineEvent snapshot."""
    observed_default = _utcnow()
    with _lock, _connect() as conn:
        conn.execute("DELETE FROM timeline_events")
        for event in events:
            conn.execute(
                """
                INSERT INTO timeline_events
                    (timeline_id, media_id, media_title, stage, stage_status,
                     source, timestamp, evidence_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.get("timeline_id"),
                    str(event.get("media_id"))
                    if event.get("media_id") is not None
                    else None,
                    event.get("media_title"),
                    event.get("stage"),
                    event.get("stage_status"),
                    event.get("source"),
                    event.get("timestamp") or observed_default,
                    json.dumps(event.get("evidence") or {}, default=str),
                ),
            )


def all_timeline_events(media_id: str | None = None) -> list[dict[str, Any]]:
    with _lock, _connect() as conn:
        if media_id is None:
            rows = conn.execute(
                "SELECT * FROM timeline_events "
                "ORDER BY timeline_id ASC, id ASC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM timeline_events WHERE media_id = ? "
                "ORDER BY id ASC",
                (str(media_id),),
            ).fetchall()
    events: list[dict[str, Any]] = []
    for row in rows:
        event = dict(row)
        raw_evidence = event.pop("evidence_json", None)
        if raw_evidence:
            try:
                event["evidence"] = json.loads(raw_evidence)
            except (TypeError, ValueError):
                event["evidence"] = {}
        else:
            event["evidence"] = {}
        events.append(event)
    return events


def replace_decision_assessments(assessments: list[dict[str, Any]]) -> None:
    """Replace the full DecisionAssessment snapshot.

    Decision assessments are derived state for the current operational picture
    and follow the same delete-and-insert pattern as the other interpreters.
    """
    observed_default = _utcnow()
    with _lock, _connect() as conn:
        conn.execute("DELETE FROM decision_assessments")
        for assessment in assessments:
            conn.execute(
                """
                INSERT INTO decision_assessments
                    (decision_id, media_id, media_title, selected_release,
                     source_application, source_indexer, candidate_count,
                     decision_reason, decision_quality, confidence, evidence_json,
                     observed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    assessment.get("decision_id"),
                    str(assessment.get("media_id"))
                    if assessment.get("media_id") is not None
                    else None,
                    assessment.get("media_title"),
                    assessment.get("selected_release"),
                    assessment.get("source_application"),
                    assessment.get("source_indexer"),
                    assessment.get("candidate_count"),
                    assessment.get("decision_reason"),
                    assessment.get("decision_quality"),
                    assessment.get("confidence"),
                    json.dumps(assessment.get("evidence") or {}, default=str),
                    assessment.get("observed_at") or observed_default,
                ),
            )


def all_decision_assessments(media_id: str | None = None) -> list[dict[str, Any]]:
    with _lock, _connect() as conn:
        if media_id is None:
            rows = conn.execute(
                "SELECT * FROM decision_assessments "
                "ORDER BY observed_at DESC, id DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM decision_assessments WHERE media_id = ? "
                "ORDER BY observed_at DESC, id DESC",
                (str(media_id),),
            ).fetchall()

    assessments: list[dict[str, Any]] = []
    for row in rows:
        assessment = dict(row)
        raw_evidence = assessment.pop("evidence_json", None)
        if raw_evidence:
            try:
                assessment["evidence"] = json.loads(raw_evidence)
            except (TypeError, ValueError):
                assessment["evidence"] = {}
        else:
            assessment["evidence"] = {}
        assessments.append(assessment)
    return assessments


def all_responsibility_assessments() -> list[dict[str, Any]]:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM responsibility_assessments "
            "ORDER BY observed_at DESC, id ASC"
        ).fetchall()

    assessments: list[dict[str, Any]] = []
    for row in rows:
        assessment = dict(row)
        for stored_key, public_key, default in (
            ("evidence_json", "evidence", []),
            ("impact_json", "impact", {}),
        ):
            raw = assessment.pop(stored_key, None)
            if raw:
                try:
                    assessment[public_key] = json.loads(raw)
                except (TypeError, ValueError):
                    assessment[public_key] = default
            else:
                assessment[public_key] = default
        assessments.append(assessment)
    return assessments


def insert_cleanup_execution(execution: dict[str, Any]) -> None:
    created_default = _utcnow()
    with _lock, _connect() as conn:
        conn.execute(
            """
            INSERT INTO cleanup_executions
                (execution_id, batch_id, media_id, media_title, qbit_hash, review_class,
                 match_strength, requested_action, execution_status,
                 recoverable_bytes, confirmation_phrase, blocking_reasons_json,
                 evidence_json, created_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                execution.get("execution_id"),
                execution.get("batch_id"),
                str(execution.get("media_id"))
                if execution.get("media_id") is not None
                else None,
                execution.get("media_title"),
                execution.get("qbit_hash"),
                execution.get("review_class"),
                execution.get("match_strength"),
                execution.get("requested_action"),
                execution.get("execution_status"),
                execution.get("recoverable_bytes"),
                execution.get("confirmation_phrase"),
                json.dumps(execution.get("blocking_reasons") or []),
                json.dumps(execution.get("evidence") or {}, default=str),
                execution.get("created_at") or created_default,
                execution.get("completed_at"),
            ),
        )


def update_cleanup_execution(execution_id: str, updates: dict[str, Any]) -> None:
    with _lock, _connect() as conn:
        conn.execute(
            """
            UPDATE cleanup_executions
            SET execution_status = ?,
                blocking_reasons_json = ?,
                evidence_json = ?,
                completed_at = ?
            WHERE execution_id = ?
            """,
            (
                updates.get("execution_status"),
                json.dumps(updates.get("blocking_reasons") or []),
                json.dumps(updates.get("evidence") or {}, default=str),
                updates.get("completed_at") or _utcnow(),
                execution_id,
            ),
        )


def all_cleanup_executions(limit: int = 100) -> list[dict[str, Any]]:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM cleanup_executions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()

    executions: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        for stored_key, public_key, default in (
            ("blocking_reasons_json", "blocking_reasons", []),
            ("evidence_json", "evidence", {}),
        ):
            raw = item.pop(stored_key, None)
            if raw:
                try:
                    item[public_key] = json.loads(raw)
                except (TypeError, ValueError):
                    item[public_key] = default
            else:
                item[public_key] = default
        executions.append(item)
    return executions


def insert_cleanup_execution_batch(batch: dict[str, Any]) -> None:
    created_default = _utcnow()
    with _lock, _connect() as conn:
        conn.execute(
            """
            INSERT INTO cleanup_execution_batches
                (batch_id, status, item_count, completed_count, failed_count,
                 planned_recoverable_bytes, actual_recovered_bytes, created_at,
                 completed_at, evidence_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                batch.get("batch_id"),
                batch.get("status"),
                batch.get("item_count"),
                batch.get("completed_count", 0),
                batch.get("failed_count", 0),
                batch.get("planned_recoverable_bytes"),
                batch.get("actual_recovered_bytes", 0),
                batch.get("created_at") or created_default,
                batch.get("completed_at"),
                json.dumps(batch.get("evidence") or {}, default=str),
            ),
        )


def update_cleanup_execution_batch(batch_id: str, updates: dict[str, Any]) -> None:
    with _lock, _connect() as conn:
        conn.execute(
            """
            UPDATE cleanup_execution_batches
            SET status = ?,
                completed_count = ?,
                failed_count = ?,
                actual_recovered_bytes = ?,
                completed_at = ?,
                evidence_json = ?
            WHERE batch_id = ?
            """,
            (
                updates.get("status"),
                updates.get("completed_count", 0),
                updates.get("failed_count", 0),
                updates.get("actual_recovered_bytes", 0),
                updates.get("completed_at") or _utcnow(),
                json.dumps(updates.get("evidence") or {}, default=str),
                batch_id,
            ),
        )


def cleanup_execution_batch(batch_id: str) -> dict[str, Any] | None:
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT * FROM cleanup_execution_batches WHERE batch_id = ? ORDER BY id DESC LIMIT 1",
            (batch_id,),
        ).fetchone()
    if not row:
        return None
    item = dict(row)
    raw = item.pop("evidence_json", None)
    if raw:
        try:
            item["evidence"] = json.loads(raw)
        except (TypeError, ValueError):
            item["evidence"] = {}
    else:
        item["evidence"] = {}
    return item


def all_cleanup_execution_batches(limit: int = 100) -> list[dict[str, Any]]:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM cleanup_execution_batches ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        raw = item.pop("evidence_json", None)
        if raw:
            try:
                item["evidence"] = json.loads(raw)
            except (TypeError, ValueError):
                item["evidence"] = {}
        else:
            item["evidence"] = {}
        out.append(item)
    return out


def projection_snapshot(key: str) -> dict[str, Any] | None:
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT * FROM projection_snapshots WHERE projection_key = ?",
            (key,),
        ).fetchone()
    if not row:
        return None
    item = dict(row)
    for stored_key, public_key, default in (
        ("payload_json", "payload", None),
        ("summary_json", "summary", {}),
    ):
        raw = item.pop(stored_key, None)
        if raw:
            try:
                item[public_key] = json.loads(raw)
            except (TypeError, ValueError):
                item[public_key] = default
        else:
            item[public_key] = default
    return item


def projection_snapshot_summary(key: str) -> dict[str, Any] | None:
    with _lock, _connect() as conn:
        row = conn.execute(
            """
            SELECT projection_key, fingerprint, summary_json, source_event_count,
                   generated_at, updated_at
            FROM projection_snapshots
            WHERE projection_key = ?
            """,
            (key,),
        ).fetchone()
    if not row:
        return None
    item = dict(row)
    raw = item.pop("summary_json", None)
    if raw:
        try:
            item["summary"] = json.loads(raw)
        except (TypeError, ValueError):
            item["summary"] = {}
    else:
        item["summary"] = {}
    return item


def upsert_projection_snapshot(
    key: str,
    fingerprint: str,
    payload: Any,
    *,
    summary: dict[str, Any] | None = None,
    source_event_count: int | None = None,
) -> None:
    now = _utcnow()
    with _lock, _connect() as conn:
        conn.execute(
            """
            INSERT INTO projection_snapshots
                (projection_key, fingerprint, payload_json, summary_json,
                 source_event_count, generated_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(projection_key) DO UPDATE SET
                fingerprint = excluded.fingerprint,
                payload_json = excluded.payload_json,
                summary_json = excluded.summary_json,
                source_event_count = excluded.source_event_count,
                generated_at = excluded.generated_at,
                updated_at = excluded.updated_at
            """,
            (
                key,
                fingerprint,
                json.dumps(payload, default=str),
                json.dumps(summary or {}, default=str),
                source_event_count,
                now,
                now,
            ),
        )


def table_fingerprint(table: str) -> dict[str, Any]:
    allowed = {
        "cleanup_events",
        "import_events",
        "library_artifacts",
        "handoff_traces",
        "cleanup_executions",
        "cleanup_execution_batches",
        "recommendations",
        "raw_events",
    }
    if table not in allowed:
        raise ValueError(f"Unsupported fingerprint table: {table}")
    with _lock, _connect() as conn:
        row = conn.execute(
            f"SELECT COUNT(*) AS count, COALESCE(MAX(id), 0) AS max_id FROM {table}"
        ).fetchone()
    return {"table": table, "count": row["count"], "max_id": row["max_id"]}


def raw_event_fingerprint(source: str, event_type: str | None = None) -> dict[str, Any]:
    with _lock, _connect() as conn:
        if event_type is None:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count, COALESCE(MAX(id), 0) AS max_id
                FROM raw_events
                WHERE source = ?
                """,
                (source,),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count, COALESCE(MAX(id), 0) AS max_id
                FROM raw_events
                WHERE source = ? AND event_type = ?
                """,
                (source, event_type),
            ).fetchone()
    return {
        "table": "raw_events",
        "source": source,
        "event_type": event_type,
        "count": row["count"],
        "max_id": row["max_id"],
    }


def completed_cleanup_execution_fingerprint() -> dict[str, Any]:
    with _lock, _connect() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS count, COALESCE(MAX(id), 0) AS max_id
            FROM cleanup_executions
            WHERE execution_status = 'Completed'
            """
        ).fetchone()
    return {
        "table": "cleanup_executions",
        "execution_status": "Completed",
        "count": row["count"],
        "max_id": row["max_id"],
    }
