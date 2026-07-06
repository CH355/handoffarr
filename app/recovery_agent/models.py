from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class PolicyDecision:
    evaluate: bool
    reasons: list[str]


@dataclass
class EvaluationResult:
    health: dict[str, Any]
    policy: PolicyDecision
    alternatives: dict[str, Any] | None
    error: str | None
    duration_ms: float


@dataclass
class RecoveryPlan:
    id: str
    torrent_hash: str
    media_id: str | None
    created_at: str
    status: str
    current_health: dict[str, Any]
    recommendation: str
    confidence: float
    reasoning: list[str]
    replacement_candidates: list[dict[str, Any]]
    planned_action: str
    job_id: str | None = None
    media_title: str | None = None
    media_type: str | None = None
    current_release: str | None = None
    evaluation_duration_ms: float = 0
    signals: dict[str, Any] | None = None
    policy_matches: list[dict[str, Any]] | None = None
    confidence_breakdown: list[dict[str, Any]] | None = None
    timeline: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
