"""SQLite storage for Handoffarr.

Stores raw collector events and correlated handoff traces. The database lives at
/data/handoffarr.sqlite3 by default and is created on first use.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("handoffarr.db")

DB_PATH = os.environ.get("HANDOFFARR_DB", "/data/handoffarr.sqlite3")

_lock = threading.Lock()


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

            CREATE INDEX IF NOT EXISTS idx_raw_events_source
                ON raw_events (source, observed_at);
            CREATE INDEX IF NOT EXISTS idx_raw_events_source_type
                ON raw_events (source, event_type, observed_at);
            CREATE INDEX IF NOT EXISTS idx_raw_events_hash
                ON raw_events (torrent_hash);
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
            """
        )
        _migrate_handoff_traces(conn)
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
) -> None:
    with _lock, _connect() as conn:
        conn.execute(
            """
            INSERT INTO raw_events
                (source, event_type, external_id, title, torrent_hash,
                 download_id, payload_json, observed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source,
                event_type,
                str(external_id) if external_id is not None else None,
                title,
                torrent_hash,
                str(download_id) if download_id is not None else None,
                json.dumps(payload, default=str),
                observed_at or _utcnow(),
            ),
        )


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


def events_for_source_since(source: str, since_iso: str) -> list[dict[str, Any]]:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM raw_events WHERE source = ? AND observed_at >= ? "
            "ORDER BY id DESC",
            (source, since_iso),
        ).fetchall()
    return [dict(r) for r in rows]


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
