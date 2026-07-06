import time
from typing import Any, Callable
from ..config import Config
from ..recovery import RecoveryProviderError
from .models import EvaluationResult
from .policy import RecoveryPolicyEngine


class RecoveryEvaluator:
    def __init__(self, policy: RecoveryPolicyEngine, alternatives: Callable[..., dict]):
        self.policy, self.alternatives = policy, alternatives

    def evaluate(self, config: Config, torrent: dict[str, Any], events: list[dict]) -> EvaluationResult:
        started = time.perf_counter()
        health = {"status": torrent.get("recovery_status"), "dead": bool(torrent.get("dead_torrent")),
                  "availability_percent": torrent.get("availability_percent"),
                  "seeders": torrent.get("seeders"), "progress": torrent.get("progress"),
                  "peers": torrent.get("peers"), "state": torrent.get("state"),
                  "health_score": torrent.get("replacement_health_score")}
        decision, alternatives, error = self.policy.evaluate(torrent), None, None
        if decision.evaluate:
            try:
                alternatives = self.alternatives(config, torrent, events, force=False)
            except RecoveryProviderError as exc:
                error = str(exc)
        return EvaluationResult(health, decision, alternatives, error,
                                round((time.perf_counter() - started) * 1000, 2))
