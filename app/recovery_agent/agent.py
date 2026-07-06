import logging
from datetime import datetime, timezone
from .. import db
from ..recovery import cached_evaluation, evaluate_torrent
from ..torrents import enrich_torrent
from .evaluator import RecoveryEvaluator
from .history import RecoveryHistory
from .planner import RecoveryPlanner
from .policy import RecoveryPolicyEngine
from .queue import RecoveryQueue
from .repository import SQLiteRecoveryRepository
from .scheduler import RecoveryScheduler

logger = logging.getLogger("handoffarr.recovery_agent")


class RecoveryAgent:
    def __init__(self, repository=None, scheduler=None, evaluator=None, planner=None):
        self.repository = repository or SQLiteRecoveryRepository()
        self.scheduler = scheduler or RecoveryScheduler()
        self._uses_default_evaluator = evaluator is None
        self.evaluator = evaluator or RecoveryEvaluator(RecoveryPolicyEngine(), evaluate_torrent)
        self.planner = planner or RecoveryPlanner()
        self.queue, self.history = RecoveryQueue(self.repository), RecoveryHistory(self.repository)

    def tick(self, config, torrents, event_loader) -> int:
        cfg = config.section("recovery_agent")
        if self._uses_default_evaluator:
            self.evaluator.policy = RecoveryPolicyEngine(cfg.get("policies"))
        settings = db.recovery_agent_settings(default_enabled=bool(cfg.get("enabled", True)),
            default_interval=int(cfg.get("evaluation_interval_minutes", 15)))
        if not self.scheduler.due(settings):
            return 0
        now, interval = datetime.now(timezone.utc), int(settings.get("interval_minutes") or 15)
        db.update_recovery_agent_settings(agent_status="Running",
            next_evaluation_at=self.scheduler.next(interval, now))
        generated = 0
        for raw in torrents:
            torrent_hash = str(raw.get("hash") or "").lower()
            torrent = enrich_torrent(raw, cached_evaluation(torrent_hash))
            job = self.queue.enqueue(str(torrent.get("hash") or ""))
            self.queue.transition(job["job_id"], "Running")
            try:
                result = self.evaluator.evaluate(config, torrent, event_loader(job["torrent_hash"]))
                plan = self.planner.create(torrent, result, job["job_id"])
                self.repository.insert_plan(plan.to_dict())
                self.history.record(plan, result)
                self.queue.transition(job["job_id"], "Completed")
                generated += 1
                logger.info("Recovery evaluation duration_ms=%.2f decision=%s confidence=%.1f candidate_count=%d",
                    result.duration_ms, plan.planned_action, plan.confidence, len(plan.replacement_candidates))
            except Exception as exc:
                self.queue.transition(job["job_id"], "Failed", str(exc))
                logger.exception("Recovery evaluation failed for %s", job["torrent_hash"])
        db.update_recovery_agent_settings(agent_status="Idle", last_evaluation_at=now.isoformat())
        return generated
