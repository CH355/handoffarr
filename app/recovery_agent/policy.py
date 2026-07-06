from typing import Any
from .models import PolicyDecision


class RecoveryPolicyEngine:
    DEFAULTS = {"availability": 5.0, "seeders": 3, "health_score": 40.0}

    def __init__(self, policies: dict[str, Any] | None = None):
        self.policies = {**self.DEFAULTS, **(policies or {})}

    def evaluate(self, torrent: dict[str, Any]) -> PolicyDecision:
        reasons = []
        if torrent.get("dead_torrent"):
            reasons.append("Dead torrent requires immediate evaluation.")
        availability = torrent.get("availability_percent")
        if availability is not None and float(availability) < self.policies["availability"]:
            reasons.append("Availability is below 5%.")
        if int(torrent.get("seeders") or 0) < self.policies["seeders"]:
            reasons.append("Seeder count is below 3.")
        score = torrent.get("replacement_health_score")
        if score is not None and float(score) < self.policies["health_score"]:
            reasons.append("Health score is below 40.")
        return PolicyDecision(bool(reasons), reasons)
