"""Execution Engine orchestrator.

Consumes approved Recovery Plans and executes them step by step.
Observable, replayable, auditable, cancellable, resumable.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from ..config import Config
from .actions import ActionRegistry
from .audit import ExecutionAuditor
from .locks import acquire_torrent_lock, release_torrent_lock
from .models import (
    ExecutionJob,
    ExecutionPlan,
    ExecutionPlanStep,
    ExecutionTimelineEvent,
)
from .queue import ExecutionQueue
from .verification import ActionVerifier

logger = logging.getLogger("handoffarr.execution_engine")


class ExecutionEngine:
    """Orchestrates execution of approved recovery plans."""

    def __init__(self, config: Config):
        self.config = config
        self.queue = ExecutionQueue()
        self.auditor = ExecutionAuditor()
        self.verifier = ActionVerifier()

    def build_plan(self, plan_id: str, torrent_hash: str) -> ExecutionPlan:
        """Build a default execution plan from a recovery plan.

        Steps:
        1. Remove Torrent
        2. Verify Removal
        3. Wait 30s
        4. Verify Pipeline State
        5. Finish
        """
        steps = [
            ExecutionPlanStep(
                step_number=1,
                action_type="RemoveTorrent",
                action_params={"delete_files": False},
                verification_type="VerifyTorrentRemoved",
                retryable=True,
            ),
            ExecutionPlanStep(
                step_number=2,
                action_type="VerifyTorrentRemoved",
                verification_type="VerifyTorrentRemoved",
                retryable=True,
            ),
            ExecutionPlanStep(
                step_number=3,
                action_type="Wait",
                action_params={"seconds": 30},
                retryable=False,
            ),
            ExecutionPlanStep(
                step_number=4,
                action_type="VerifyPipelineState",
                verification_type="VerifyPipelineState",
                retryable=True,
            ),
        ]
        return ExecutionPlan(plan_id=plan_id, torrent_hash=torrent_hash, steps=steps)

    def submit(self, plan_id: str, torrent_hash: str, mode: str = "manual") -> ExecutionJob:
        """Submit a recovery plan for execution. Creates a Pending job."""
        job = self.queue.create_job(plan_id, torrent_hash, mode=mode)
        plan = self.build_plan(plan_id, torrent_hash)
        job.total_steps = len(plan.steps)
        self.queue.update_job(job)
        self._add_timeline(job, "submitted", f"Execution submitted for plan {plan_id}")
        logger.info("Execution submitted execution_id=%s plan_id=%s", job.execution_id, plan_id)
        return job

    def approve(self, execution_id: str) -> ExecutionJob | None:
        """Approve a pending execution job."""
        job = self.queue.approve_job(execution_id)
        if job:
            self._add_timeline(job, "approved", "Execution approved")
            logger.info("Execution approved execution_id=%s", execution_id)
        return job

    def cancel(self, execution_id: str) -> ExecutionJob | None:
        """Cancel an execution job."""
        job = self.queue.cancel_job(execution_id)
        if job:
            self._add_timeline(job, "cancelled", "Execution cancelled")
            logger.info("Execution cancelled execution_id=%s", execution_id)
        return job

    def retry(self, execution_id: str) -> ExecutionJob | None:
        """Retry a failed or cancelled execution job."""
        job = self.queue.retry_job(execution_id)
        if job:
            self._add_timeline(job, "retry", f"Execution retry #{job.retry_count}")
            logger.info("Execution retry execution_id=%s retry_count=%s", execution_id, job.retry_count)
        return job

    def run_job(self, execution_id: str) -> ExecutionJob | None:
        """Run an approved execution job to completion.

        Acquires torrent lock, executes steps, records audit and timeline.
        """
        job = self.queue.get_job(execution_id)
        if job is None or job.status != "Approved":
            logger.warning("Execution not runnable execution_id=%s status=%s", execution_id, job.status if job else None)
            return job

        # Acquire lock
        if not acquire_torrent_lock(job.torrent_hash, job.execution_id, timeout_seconds=30.0):
            job.error = "Could not acquire torrent lock (another execution in progress)"
            job.status = "Failed"
            self.queue.update_job(job)
            return job

        try:
            job.status = "Running"
            job.started_at = _utcnow()
            self.queue.update_job(job)
            self.auditor.record_start(job)
            self._add_timeline(job, "started", "Execution started")

            plan = self.build_plan(job.plan_id, job.torrent_hash)

            for step in plan.steps:
                if job.status in {"Cancelled", "Failed"}:
                    break

                job.current_step = step.step_number
                job.current_action = step.action_type
                self.queue.update_job(job)

                self._add_timeline(
                    job,
                    "step_started",
                    f"Step {step.step_number}: {step.action_type}",
                    {"step_number": step.step_number, "action": step.action_type},
                )

                # Execute with retry policy
                action_result = self._execute_step_with_retry(job, step)
                job.results.append(action_result.to_dict())
                self.auditor.record_action(job, action_result)

                if action_result.success:
                    self._add_timeline(
                        job,
                        "step_completed",
                        f"Step {step.step_number} completed",
                        {"step_number": step.step_number},
                    )
                else:
                    job.error = action_result.error
                    job.status = "Failed"
                    self._add_timeline(
                        job,
                        "step_failed",
                        f"Step {step.step_number} failed: {action_result.error}",
                        {"step_number": step.step_number, "error": action_result.error},
                    )
                    break

            if job.status == "Running":
                job.status = "Completed"
                job.error = None
                self._add_timeline(job, "completed", "Execution completed")
                self.auditor.record_completion(job, "Completed")
            elif job.status == "Failed":
                self.auditor.record_completion(job, "Failed")

            job.completed_at = _utcnow()
            job.current_action = None
            self.queue.update_job(job)

        finally:
            release_torrent_lock(job.torrent_hash, job.execution_id)

        return job

    def _execute_step_with_retry(
        self,
        job: ExecutionJob,
        step: ExecutionPlanStep,
    ) -> Any:  # ExecutionActionResult
        """Execute a step with exponential backoff retry."""
        from .models import ExecutionActionResult

        action = ActionRegistry.create(step.action_type, self.config, self.verifier)
        if action is None:
            return ExecutionActionResult(
                action_type=step.action_type,
                step_number=step.step_number,
                success=False,
                duration_ms=0.0,
                error=f"Unknown action type: {step.action_type}",
            )

        max_attempts = job.max_retries + 1 if step.retryable else 1
        last_result = None

        for attempt in range(max_attempts):
            last_result = action.run(job.torrent_hash, step.step_number, step.action_params)
            if last_result.success:
                last_result.retry_count = attempt
                return last_result
            if attempt < max_attempts - 1:
                backoff = min(2 ** attempt, 60)  # cap at 60s
                logger.info(
                    "Execution retry execution_id=%s step=%s attempt=%s backoff=%s",
                    job.execution_id, step.step_number, attempt + 1, backoff,
                )
                time.sleep(backoff)

        if last_result:
            last_result.retry_count = max_attempts - 1
        return last_result

    def _add_timeline(
        self,
        job: ExecutionJob,
        event_type: str,
        label: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        event = ExecutionTimelineEvent(
            event_type=event_type,
            label=label,
            timestamp=_utcnow(),
            details=details,
        )
        job.timeline.append(event)

    def status(self) -> dict[str, Any]:
        """Return aggregate status for the dashboard."""
        all_jobs, _ = self.queue.list_jobs(limit=10000)
        statuses = {}
        for s in ("Pending", "Approved", "Running", "Waiting", "Completed", "Failed", "Cancelled", "Rolled Back"):
            statuses[s] = sum(1 for j in all_jobs if j.status == s)
        durations = [
            j for j in all_jobs
            if j.started_at and j.completed_at
        ]
        avg_duration = 0.0
        if durations:
            total = sum(
                (_parse_iso(j.completed_at) - _parse_iso(j.started_at)).total_seconds()
                for j in durations
            )
            avg_duration = round(total / len(durations), 1)

        return {
            "queue_counts": statuses,
            "total_jobs": len(all_jobs),
            "average_duration_seconds": avg_duration,
            "recent_jobs": [j.to_dict() for j in all_jobs[:5]],
        }


def _utcnow() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: str) -> Any:
    from datetime import datetime
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
