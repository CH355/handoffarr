"""Execution Engine queue and persistence.

Jobs are persisted to SQLite via app/db.py functions.
"""
from __future__ import annotations

import json
import time
from typing import Any

from .. import db
from .models import ExecutionJob, ExecutionTimelineEvent, create_execution_id


class ExecutionQueue:
    """Manages execution job lifecycle and persistence."""

    def create_job(
        self,
        plan_id: str,
        torrent_hash: str,
        mode: str = "manual",
        max_retries: int = 3,
    ) -> ExecutionJob:
        job = ExecutionJob(
            execution_id=create_execution_id(),
            plan_id=plan_id,
            torrent_hash=torrent_hash,
            status="Pending",
            mode=mode,
            created_at=_utcnow(),
            max_retries=max_retries,
        )
        _persist_job(job)
        return job

    def approve_job(self, execution_id: str) -> ExecutionJob | None:
        job = _load_job(execution_id)
        if job is None or job.status != "Pending":
            return None
        job.status = "Approved"
        job.approved_at = _utcnow()
        _persist_job(job)
        return job

    def cancel_job(self, execution_id: str) -> ExecutionJob | None:
        job = _load_job(execution_id)
        if job is None or job.status in {"Completed", "Failed", "Cancelled", "Rolled Back"}:
            return None
        job.status = "Cancelled"
        job.completed_at = _utcnow()
        _persist_job(job)
        return job

    def retry_job(self, execution_id: str) -> ExecutionJob | None:
        job = _load_job(execution_id)
        if job is None or job.status not in {"Failed", "Cancelled"}:
            return None
        job.status = "Approved"
        job.error = None
        job.retry_count += 1
        job.completed_at = None
        _persist_job(job)
        return job

    def list_jobs(
        self,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ExecutionJob], int]:
        return _jobs_page(status, limit, offset)

    def get_job(self, execution_id: str) -> ExecutionJob | None:
        return _load_job(execution_id)

    def update_job(self, job: ExecutionJob) -> None:
        _persist_job(job)


def _utcnow() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _persist_job(job: ExecutionJob) -> None:
    """Upsert execution job into the database."""
    with db._lock, db._connect() as conn:
        conn.execute(
            """
            INSERT INTO execution_jobs (
                execution_id, plan_id, torrent_hash, status, mode,
                created_at, approved_at, started_at, completed_at,
                current_step, total_steps, current_action, error,
                retry_count, max_retries, rollback_available,
                audit_log_json, timeline_json, results_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(execution_id) DO UPDATE SET
                status = excluded.status,
                approved_at = excluded.approved_at,
                started_at = excluded.started_at,
                completed_at = excluded.completed_at,
                current_step = excluded.current_step,
                total_steps = excluded.total_steps,
                current_action = excluded.current_action,
                error = excluded.error,
                retry_count = excluded.retry_count,
                max_retries = excluded.max_retries,
                rollback_available = excluded.rollback_available,
                audit_log_json = excluded.audit_log_json,
                timeline_json = excluded.timeline_json,
                results_json = excluded.results_json
            """,
            (
                job.execution_id,
                job.plan_id,
                job.torrent_hash,
                job.status,
                job.mode,
                job.created_at,
                job.approved_at,
                job.started_at,
                job.completed_at,
                job.current_step,
                job.total_steps,
                job.current_action,
                job.error,
                job.retry_count,
                job.max_retries,
                1 if job.rollback_available else 0,
                json.dumps([a.to_dict() for a in job.audit_log], default=str),
                json.dumps([t.to_dict() for t in job.timeline], default=str),
                json.dumps([r.to_dict() for r in job.results], default=str),
            ),
        )


def _load_job(execution_id: str) -> ExecutionJob | None:
    with db._connect() as conn:
        row = conn.execute(
            "SELECT * FROM execution_jobs WHERE execution_id = ? LIMIT 1",
            (execution_id,),
        ).fetchone()
    if not row:
        return None
    return _decode_job(row)


def _jobs_page(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[ExecutionJob], int]:
    where = "WHERE status = ?" if status else ""
    params: list[Any] = [status] if status else []
    with db._connect() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS count FROM execution_jobs {where}",
            params,
        ).fetchone()["count"]
        rows = conn.execute(
            f"SELECT * FROM execution_jobs {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
    return [_decode_job(row) for row in rows], int(total)


def _decode_job(row: Any) -> ExecutionJob:
    job = ExecutionJob(
        execution_id=row["execution_id"],
        plan_id=row["plan_id"],
        torrent_hash=row["torrent_hash"],
        status=row["status"],
        mode=row["mode"],
        created_at=row["created_at"],
        approved_at=row["approved_at"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        current_step=row["current_step"] or 0,
        total_steps=row["total_steps"] or 0,
        current_action=row["current_action"],
        error=row["error"],
        retry_count=row["retry_count"] or 0,
        max_retries=row["max_retries"] or 3,
        rollback_available=bool(row["rollback_available"]),
    )
    for source, target, default in (
        ("audit_log_json", "audit_log", []),
        ("timeline_json", "timeline", []),
        ("results_json", "results", []),
    ):
        raw = row[source] if source in row.keys() else None
        if raw:
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    setattr(job, target, data)
            except (TypeError, ValueError):
                pass
    return job
