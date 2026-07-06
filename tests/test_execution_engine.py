from unittest import TestCase

from app.execution_engine.models import (
    ExecutionActionResult,
    ExecutionAuditEntry,
    ExecutionJob,
    ExecutionPlan,
    ExecutionPlanStep,
    ExecutionTimelineEvent,
    create_execution_id,
)
from app.execution_engine.locks import (
    acquire_torrent_lock,
    force_release_all,
    is_locked,
    lock_holder,
    release_torrent_lock,
)
from app.execution_engine.audit import ExecutionAuditor
from app.execution_engine.actions import ActionRegistry
from app.execution_engine.verification import ActionVerifier
from app.execution_engine.queue import ExecutionQueue
from app.execution_engine.executor import ExecutionEngine
from app.config import Config


class ExecutionEngineTests(TestCase):
    def test_model_creation(self):
        job = ExecutionJob(
            execution_id=create_execution_id(),
            plan_id="plan-1",
            torrent_hash="hash-1",
            status="Pending",
            mode="manual",
            created_at="2024-01-01T00:00:00Z",
        )
        self.assertEqual(job.status, "Pending")
        d = job.to_dict()
        self.assertEqual(d["status"], "Pending")
        self.assertEqual(d["mode"], "manual")

    def test_action_result_model(self):
        result = ExecutionActionResult(
            action_type="RemoveTorrent",
            step_number=1,
            success=True,
            duration_ms=123.4,
            verification_passed=True,
        )
        d = result.to_dict()
        self.assertTrue(d["success"])
        self.assertTrue(d["verification_passed"])

    def test_plan_model(self):
        step = ExecutionPlanStep(
            step_number=1,
            action_type="RemoveTorrent",
            action_params={"delete_files": False},
        )
        plan = ExecutionPlan("plan-1", "hash-1", [step])
        self.assertEqual(len(plan.to_dict()["steps"]), 1)

    def test_lock_acquire_release(self):
        force_release_all()
        self.assertTrue(acquire_torrent_lock("torrent-1", "exec-1"))
        self.assertTrue(is_locked("torrent-1"))
        self.assertEqual(lock_holder("torrent-1"), "exec-1")
        # Same exec can re-acquire
        self.assertTrue(acquire_torrent_lock("torrent-1", "exec-1"))
        # Different exec cannot acquire
        self.assertFalse(acquire_torrent_lock("torrent-1", "exec-2", timeout_seconds=0.1))
        # Release
        self.assertTrue(release_torrent_lock("torrent-1", "exec-1"))
        self.assertFalse(is_locked("torrent-1"))
        force_release_all()

    def test_lock_wrong_release_blocked(self):
        force_release_all()
        acquire_torrent_lock("torrent-2", "exec-3")
        self.assertFalse(release_torrent_lock("torrent-2", "exec-4"))
        release_torrent_lock("torrent-2", "exec-3")
        force_release_all()

    def test_audit_log(self):
        job = ExecutionJob(
            execution_id=create_execution_id(),
            plan_id="plan-1",
            torrent_hash="hash-1",
            status="Running",
            mode="manual",
            created_at="2024-01-01T00:00:00Z",
        )
        auditor = ExecutionAuditor()
        start = auditor.record_start(job)
        self.assertEqual(start.result, "started")
        self.assertEqual(len(job.audit_log), 1)

        result = ExecutionActionResult(
            action_type="RemoveTorrent",
            step_number=1,
            success=True,
            duration_ms=150.0,
            verification_passed=True,
        )
        action = auditor.record_action(job, result)
        self.assertEqual(action.result, "success")
        self.assertEqual(action.verification, "passed")
        self.assertEqual(len(job.audit_log), 2)

        end = auditor.record_completion(job, "Completed")
        self.assertEqual(end.result, "completed")
        self.assertEqual(len(job.audit_log), 3)

    def test_action_registry(self):
        actions = ActionRegistry.list_actions()
        self.assertIn("RemoveTorrent", actions)
        self.assertIn("VerifyTorrentRemoved", actions)
        self.assertIn("Wait", actions)
        self.assertIn("VerifyPipelineState", actions)
        self.assertIn("RefreshAlternatives", actions)

        config = Config(None, "/tmp/nonexistent.yaml", False)
        unknown = ActionRegistry.create("UnknownAction", config)
        self.assertIsNone(unknown)

        wait_action = ActionRegistry.create("Wait", config)
        self.assertIsNotNone(wait_action)
        self.assertEqual(wait_action.action_type, "Wait")

    def test_wait_action(self):
        config = Config(None, "/tmp/nonexistent.yaml", False)
        wait_action = ActionRegistry.create("Wait", config)
        result = wait_action.run("hash-1", 1, {"seconds": 0})
        self.assertTrue(result.success)
        self.assertEqual(result.action_type, "Wait")

    def test_verifier_wait(self):
        verifier = ActionVerifier()
        ok, msg = verifier.verify("Wait", {"seconds": 30}, {"waited_seconds": 30})
        self.assertTrue(ok)
        self.assertIsNone(msg)

        ok, msg = verifier.verify("Wait", {"seconds": 30}, {"waited_seconds": 10})
        self.assertFalse(ok)
        self.assertIn("Waited 10s", msg)

    def test_verifier_default(self):
        verifier = ActionVerifier()
        ok, msg = verifier.verify("UnknownAction", {}, {"error": "boom"})
        self.assertFalse(ok)

        ok, msg = verifier.verify("UnknownAction", {}, {"result": "ok"})
        self.assertTrue(ok)

    def test_queue_lifecycle(self):
        import os
        import tempfile
        import app.db as db

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "handoffarr.sqlite3")
            os.environ["HANDOFFARR_DB"] = db_path
            db.DB_PATH = db_path
            db.init_db()

            queue = ExecutionQueue()
            job = queue.create_job("plan-123", "abc123")
            self.assertEqual(job.status, "Pending")

            loaded = queue.get_job(job.execution_id)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.status, "Pending")

            approved = queue.approve_job(job.execution_id)
            self.assertEqual(approved.status, "Approved")

            jobs, total = queue.list_jobs(limit=10)
            self.assertEqual(len(jobs), 1)
            self.assertEqual(total, 1)

            cancelled = queue.cancel_job(job.execution_id)
            self.assertEqual(cancelled.status, "Cancelled")

            retried = queue.retry_job(job.execution_id)
            self.assertEqual(retried.status, "Approved")
            self.assertEqual(retried.retry_count, 1)

    def test_executor_submit_approve_cancel_retry(self):
        import os
        import tempfile
        import app.db as db

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "handoffarr.sqlite3")
            os.environ["HANDOFFARR_DB"] = db_path
            db.DB_PATH = db_path
            db.init_db()

            config = Config(None, "/tmp/nonexistent.yaml", False)
            engine = ExecutionEngine(config)

            job = engine.submit("plan-test", "torrent-hash-123")
            self.assertEqual(job.status, "Pending")
            self.assertEqual(job.total_steps, 4)

            approved = engine.approve(job.execution_id)
            self.assertEqual(approved.status, "Approved")

            status = engine.status()
            self.assertEqual(status["total_jobs"], 1)
            self.assertEqual(status["queue_counts"]["Approved"], 1)

            cancelled = engine.cancel(job.execution_id)
            self.assertEqual(cancelled.status, "Cancelled")

            retried = engine.retry(job.execution_id)
            self.assertEqual(retried.status, "Approved")
            self.assertEqual(retried.retry_count, 1)

    def test_executor_build_plan(self):
        config = Config(None, "/tmp/nonexistent.yaml", False)
        engine = ExecutionEngine(config)
        plan = engine.build_plan("plan-test", "torrent-hash-123")
        self.assertEqual(len(plan.steps), 4)
        self.assertEqual(plan.steps[0].action_type, "RemoveTorrent")
        self.assertEqual(plan.steps[1].action_type, "VerifyTorrentRemoved")
        self.assertEqual(plan.steps[2].action_type, "Wait")
        self.assertEqual(plan.steps[3].action_type, "VerifyPipelineState")

    def test_executor_timeline(self):
        import os
        import tempfile
        import app.db as db

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "handoffarr.sqlite3")
            os.environ["HANDOFFARR_DB"] = db_path
            db.DB_PATH = db_path
            db.init_db()

            config = Config(None, "/tmp/nonexistent.yaml", False)
            engine = ExecutionEngine(config)
            job = engine.submit("plan-test", "torrent-hash-123")
            self.assertTrue(len(job.timeline) > 0)
            self.assertEqual(job.timeline[0].event_type, "submitted")
