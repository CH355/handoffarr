from datetime import datetime, timezone
from uuid import uuid4
from .models import EvaluationResult, RecoveryPlan


class RecoveryPlanner:
    def create(self, torrent: dict, result: EvaluationResult, job_id: str) -> RecoveryPlan:
        created_at = datetime.now(timezone.utc).isoformat()
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
            confidence = float(selected.get("score") or 0) + (
                5 if torrent.get("dead_torrent") else 0
            )
        if result.error:
            confidence -= 20
        weights = [
            ("Availability", 35), ("Seeders", 25), ("Quality", 20),
            ("Age", 10), ("Indexer", 5), ("Custom Formats", 5),
        ]
        confidence = round(max(0, min(100, confidence)), 1)
        breakdown = [
            {"signal": label, "weight": weight, "contribution": round(confidence * weight / 100, 1)}
            for label, weight in weights
        ]
        policy_matches = [
            {"policy": reason.split(".")[0], "matched": True, "reason": reason}
            for reason in result.policy.reasons
        ]
        timeline = [
            {"type": "evaluation_started", "label": "Evaluation started", "timestamp": created_at},
            {"type": "policy_matched", "label": "Policy matched", "timestamp": created_at,
             "details": {"count": len(policy_matches)}},
        ]
        if result.policy.evaluate:
            timeline.append({"type": "alternatives_requested", "label": "Alternatives requested", "timestamp": created_at})
        timeline.extend([
            {"type": "scoring_complete", "label": "Scoring complete", "timestamp": created_at,
             "details": {"candidate_count": len(alternatives.get("candidates") or [])}},
            {"type": "recommendation_created", "label": "Recommendation created", "timestamp": created_at,
             "details": {"recommendation": action}},
            {"type": "plan_stored", "label": "Plan stored", "timestamp": created_at},
        ])
        signals = {
            **result.health,
            "quality": (selected or {}).get("quality"),
            "age_days": (selected or {}).get("age_days"),
            "indexer": (selected or {}).get("indexer"),
            "custom_format_score": (selected or {}).get("custom_format_score"),
            "rejected": (selected or {}).get("rejected"),
            "reason": (selected or {}).get("rejection_reason"),
        }
        media_type = torrent.get("media_type")
        if str(media_type or "").lower() in {"series", "tv"}:
            media_type = "Episode"
        return RecoveryPlan(
            f"recovery-plan-{uuid4()}", str(torrent.get("hash") or "").lower(),
            str(alternatives["media_id"]) if alternatives.get("media_id") is not None else None,
            created_at, "Proposed", result.health, action, confidence,
            list(dict.fromkeys(reasoning)), alternatives.get("candidates") or [],
            action, job_id, alternatives.get("media_title") or torrent.get("media_title"),
            media_type, torrent.get("current_release"),
            result.duration_ms, signals, policy_matches, breakdown, timeline)
