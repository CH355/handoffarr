from typing import Any


def compare_plans(
    previous: dict[str, Any] | None, current: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    def nested(plan: dict[str, Any] | None, key: str) -> Any:
        return (plan or {}).get("current_health", {}).get(key)

    candidates_before = (previous or {}).get("replacement_candidates") or []
    candidates_now = current.get("replacement_candidates") or []
    return {
        "health": {"previous": nested(previous, "status"), "current": nested(current, "status")},
        "confidence": {"previous": (previous or {}).get("confidence"), "current": current.get("confidence")},
        "recommendation": {"previous": (previous or {}).get("recommendation"), "current": current.get("recommendation")},
        "candidate_count": {"previous": len(candidates_before), "current": len(candidates_now)},
        "best_score": {
            "previous": max((candidate.get("score", 0) for candidate in candidates_before), default=None),
            "current": max((candidate.get("score", 0) for candidate in candidates_now), default=None),
        },
    }
