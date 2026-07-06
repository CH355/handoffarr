from datetime import datetime, timezone
from uuid import uuid4
from .models import EvaluationResult, RecoveryPlan


class RecoveryPlanner:
    def create(self, torrent: dict, result: EvaluationResult, job_id: str) -> RecoveryPlan:
        alternatives = result.alternatives or {}
        selected = alternatives.get("recommended_candidate")
        reasoning = list(result.policy.reasons)
        if torrent.get("dead_reason"):
            reasoning.append(str(torrent["dead_reason"]))
        reasoning.extend(alternatives.get("recommendation_reasons") or [])
        if selected:
            reasoning.append(f"Best replacement has {selected.get('seeders', 0)} seeders.")
        if result.error:
            reasoning.append(result.error)
        action = "Replace" if selected else "Monitor" if reasoning else "None"
        confidence = 45 + (20 if torrent.get("dead_torrent") else 0)
        if selected:
            confidence += 15 + float(selected.get("score") or 0) * .2
        if result.error:
            confidence -= 20
        return RecoveryPlan(
            f"recovery-plan-{uuid4()}", str(torrent.get("hash") or "").lower(),
            str(alternatives["media_id"]) if alternatives.get("media_id") is not None else None,
            datetime.now(timezone.utc).isoformat(), "Proposed", result.health, action,
            round(max(0, min(100, confidence)), 1), list(dict.fromkeys(reasoning)),
            alternatives.get("candidates") or [], action, job_id)
