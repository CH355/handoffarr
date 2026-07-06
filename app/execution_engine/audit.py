"""Execution Engine audit log.

Persist who, when, what, duration, result, verification, and error
for every execution step.
"""
from __future__ import annotations

import time
from typing import Any

from .models import ExecutionAuditEntry, ExecutionJob, create_audit_id


class ExecutionAuditor:
    """Records audit entries for execution steps."""

    def record(
        self,
        job: ExecutionJob,
        action_type: str,
        step_number: int,
        what: str,
        duration_ms: float,
        result: str,
        verification: str | None = None,
        error: str | None = None,
        who: str | None = None,
    ) -> ExecutionAuditEntry:
        entry = ExecutionAuditEntry(
            audit_id=create_audit_id(),
            execution_id=job.execution_id,
            action_type=action_type,
            step_number=step_number,
            who=who or "system",
            when=_utcnow(),
            what=what,
            duration_ms=duration_ms,
            result=result,
            verification=verification,
            error=error,
        )
        job.audit_log.append(entry)
        return entry

    def record_start(self, job: ExecutionJob) -> ExecutionAuditEntry:
        return self.record(
            job=job,
            action_type="ExecutionStart",
            step_number=0,
            what="Execution started",
            duration_ms=0.0,
            result="started",
        )

    def record_action(
        self,
        job: ExecutionJob,
        action_result: Any,  # ExecutionActionResult
    ) -> ExecutionAuditEntry:
        from .models import ExecutionActionResult

        if not isinstance(action_result, ExecutionActionResult):
            raise TypeError("Expected ExecutionActionResult")
        return self.record(
            job=job,
            action_type=action_result.action_type,
            step_number=action_result.step_number,
            what=f"Ran {action_result.action_type}",
            duration_ms=action_result.duration_ms,
            result="success" if action_result.success else "failure",
            verification="passed" if action_result.verification_passed else "failed",
            error=action_result.error,
        )

    def record_completion(self, job: ExecutionJob, status: str) -> ExecutionAuditEntry:
        return self.record(
            job=job,
            action_type="ExecutionEnd",
            step_number=job.current_step,
            what=f"Execution {status.lower()}",
            duration_ms=0.0,
            result=status.lower(),
        )


def _utcnow() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
