from datetime import datetime, timedelta, timezone
from unittest import TestCase

from app.recovery_agent.history import RecoveryHistory
from app.recovery_agent.models import EvaluationResult, PolicyDecision
from app.recovery_agent.planner import RecoveryPlanner
from app.recovery_agent.policy import RecoveryPolicyEngine
from app.recovery_agent.queue import RecoveryQueue
from app.recovery_agent.scheduler import RecoveryScheduler


class Repository:
    def __init__(self):
        self.jobs = {}
        self.history = []

    def insert_job(self, job):
        self.jobs[job["job_id"]] = dict(job)

    def update_job(self, job_id, **values):
        self.jobs[job_id].update(values)

    def list_jobs(self, limit):
        return list(self.jobs.values())[-limit:]

    def insert_history(self, entry):
        self.history.append(entry)


class RecoveryAgentComponentTests(TestCase):
    def test_scheduler_obeys_enabled_due_time_and_interval(self):
        scheduler = RecoveryScheduler()
        now = datetime.now(timezone.utc)
        self.assertFalse(scheduler.due({"enabled": False}, now))
        self.assertTrue(scheduler.due({"enabled": True}, now))
        self.assertFalse(
            scheduler.due(
                {
                    "enabled": True,
                    "next_evaluation_at": (now + timedelta(minutes=5)).isoformat(),
                },
                now,
            )
        )
        self.assertIn("T", scheduler.next(15, now))

    def test_queue_persists_state_transitions(self):
        repository = Repository()
        queue = RecoveryQueue(repository)
        job = queue.enqueue("ABC")
        self.assertEqual(job["status"], "Queued")
        queue.transition(job["job_id"], "Running")
        queue.transition(job["job_id"], "Completed")
        self.assertEqual(repository.jobs[job["job_id"]]["status"], "Completed")

    def test_policy_engine_explains_unhealthy_inputs(self):
        decision = RecoveryPolicyEngine().evaluate(
            {
                "dead_torrent": True,
                "availability_percent": 0,
                "seeders": 0,
                "replacement_health_score": 20,
            }
        )
        self.assertTrue(decision.evaluate)
        self.assertEqual(len(decision.reasons), 4)

    def test_planner_generates_explainable_non_executable_plan(self):
        result = EvaluationResult(
            health={"dead": True},
            policy=PolicyDecision(True, ["Dead torrent."]),
            alternatives={
                "media_id": 42,
                "recommendation_reasons": ["matches quality profile"],
                "recommended_candidate": {"seeders": 126, "score": 90},
                "candidates": [
                    {"release_name": "Better", "seeders": 126, "recommended": True}
                ],
            },
            error=None,
            duration_ms=12,
        )
        plan = RecoveryPlanner().create(
            {"hash": "ABC", "dead_torrent": True, "dead_reason": "Zero seeders."},
            result,
            "job-1",
        )
        self.assertEqual(plan.planned_action, "Replace")
        self.assertGreater(plan.confidence, 90)
        self.assertIn("Best replacement has 126 seeders.", plan.reasoning)
        self.assertEqual(plan.status, "Proposed")

    def test_history_appends_evaluation_analytics(self):
        repository = Repository()
        result = EvaluationResult(
            {"dead": True}, PolicyDecision(True, []), None, None, 8.5
        )
        plan = RecoveryPlanner().create(
            {"hash": "abc", "dead_torrent": True}, result, "job-1"
        )
        history = RecoveryHistory(repository)
        history.record(plan, result)
        history.record(plan, result)
        self.assertEqual(len(repository.history), 2)
        self.assertEqual(repository.history[0]["evaluation_duration_ms"], 8.5)
