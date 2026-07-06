from datetime import datetime, timezone
from uuid import uuid4
from .models import EvaluationResult, RecoveryPlan


class RecoveryHistory:
    def __init__(self, repository):
        self.repository = repository

    def record(self, plan: RecoveryPlan, result: EvaluationResult) -> None:
        selected = next((c for c in plan.replacement_candidates if c.get("recommended")), None)
        self.repository.insert_history({
            "history_id": f"recovery-history-{uuid4()}", "job_id": plan.job_id,
            "plan_id": plan.id, "timestamp": datetime.now(timezone.utc).isoformat(),
            "torrent_hash": plan.torrent_hash, "health": plan.current_health,
            "recommendation": plan.recommendation, "confidence": plan.confidence,
            "selected_candidate": selected, "evaluation_duration_ms": result.duration_ms,
            "candidate_count": len(plan.replacement_candidates), "decision": plan.planned_action})
