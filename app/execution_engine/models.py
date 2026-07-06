"""Execution Engine data models.

All models are plain dataclasses with to_dict() for JSON serialization.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ExecutionActionResult:
    action_type: str
    step_number: int
    success: bool
    duration_ms: float
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    verification_passed: bool = False
    retry_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionTimelineEvent:
    event_type: str
    label: str
    timestamp: str
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionAuditEntry:
    audit_id: str
    execution_id: str
    action_type: str
    step_number: int
    who: str | None
    when: str
    what: str
    duration_ms: float
    result: str
    verification: str | None
    error: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionJob:
    execution_id: str
    plan_id: str
    torrent_hash: str
    status: str  # Pending, Approved, Running, Waiting, Completed, Failed, Cancelled, Rolled Back
    mode: str  # manual, assisted, automatic
    created_at: str
    approved_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    current_step: int = 0
    total_steps: int = 0
    current_action: str | None = None
    error: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    rollback_available: bool = False
    audit_log: list[ExecutionAuditEntry] = field(default_factory=list)
    timeline: list[ExecutionTimelineEvent] = field(default_factory=list)
    results: list[ExecutionActionResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["audit_log"] = [e.to_dict() for e in self.audit_log]
        d["timeline"] = [e.to_dict() for e in self.timeline]
        d["results"] = [r.to_dict() for r in self.results]
        return d


@dataclass
class ExecutionPlanStep:
    step_number: int
    action_type: str
    action_params: dict[str, Any] = field(default_factory=dict)
    verification_type: str | None = None
    verification_params: dict[str, Any] = field(default_factory=dict)
    wait_seconds: int = 0
    retryable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ExecutionPlan:
    def __init__(self, plan_id: str, torrent_hash: str, steps: list[ExecutionPlanStep]):
        self.plan_id = plan_id
        self.torrent_hash = torrent_hash
        self.steps = steps

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "torrent_hash": self.torrent_hash,
            "steps": [s.to_dict() for s in self.steps],
        }


def create_execution_id() -> str:
    return f"execution-{uuid4()}"


def create_audit_id() -> str:
    return f"audit-{uuid4()}"
