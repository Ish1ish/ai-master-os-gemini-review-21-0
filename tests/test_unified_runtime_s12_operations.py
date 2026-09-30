import tempfile
import unittest
from pathlib import Path

from unified_runtime.production import UnifiedRuntimeProductionService


class TestS12ProductionizationOperations(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = UnifiedRuntimeProductionService(self.tmp.name)

    def tearDown(self):
        self.service.close()
        self.tmp.cleanup()

    def _payload(self, run_id="UR-S12-001"):
        return {
            "run_id": run_id,
            "project_id": "demo",
            "strategy_id": "STRAT-A",
            "intent": "Validate a low-cost AI workflow",
            "goal": "Prove a bounded next step",
            "audience": "Egypt SMB founders",
        }

    def test_health_is_explicit_and_safe(self):
        health = self.service.health()
        self.assertEqual(health["status"], "HEALTHY")
        self.assertFalse(health["external_action_capability"])
        self.assertFalse(health["memory_write"])

    def test_readiness_checks_persistence(self):
        ready = self.service.readiness()
        self.assertEqual(ready["status"], "READY")
        self.assertTrue(ready["trace_store_available"])
        self.assertTrue(Path(ready["persistence_root"]).exists())

    def test_run_updates_operational_metrics(self):
        result = self.service.run(self._payload())
        self.assertEqual(result["status"], "PASS")
        metrics = self.service.metrics.as_dict()
        self.assertEqual(metrics["total_runs"], 1)
        self.assertEqual(metrics["successful_runs"], 1)
        self.assertEqual(metrics["last_run_id"], "UR-S12-001")

    def test_replay_is_counted_without_new_persistence(self):
        self.service.run(self._payload())
        second = self.service.run(self._payload())
        self.assertEqual(second["persistence"]["status"], "IDEMPOTENT_REPLAY")
        self.assertEqual(self.service.metrics.as_dict()["replayed_runs"], 1)

    def test_recover_from_persistence(self):
        self.service.run(self._payload("UR-S12-002"))
        recovered = self.service.recover_run("UR-S12-002", "demo")
        self.assertEqual(recovered["status"], "RECOVERED_FROM_PERSISTENCE")
        self.assertTrue(recovered["recovered"])
        self.assertFalse(recovered["external_action"])
        self.assertFalse(recovered["memory_write"])

    def test_missing_recovery_is_bounded_and_explicit(self):
        recovered = self.service.recover_run("missing", "demo")
        self.assertEqual(recovered["status"], "NOT_FOUND")
        self.assertFalse(recovered["recovered"])

    def test_retry_policy_is_bounded(self):
        original = self.service.entrypoint.run
        calls = {"count": 0}

        def flaky(request):
            calls["count"] += 1
            if calls["count"] == 1:
                return {
                    "status": "BLOCKED",
                    "reason": "runtime_error",
                    "external_action": False,
                    "memory_write": False,
                }
            return {"status": "PASS", "run_id": "UR-S12-003", "project_id": "demo"}

        self.service.entrypoint.run = flaky
        try:
            result = self.service.run_with_retry(self._payload("UR-S12-003"), max_attempts=2)
        finally:
            self.service.entrypoint.run = original
        self.assertEqual(calls["count"], 2)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["operations"]["attempts"], 2)
        self.assertTrue(result["operations"]["recovered"])

    def test_invalid_retry_bound_fails_closed(self):
        with self.assertRaises(ValueError):
            self.service.run_with_retry(self._payload(), max_attempts=0)

    def test_operational_snapshot_is_complete(self):
        snapshot = self.service.operational_snapshot()
        self.assertEqual(snapshot["health"], "HEALTHY")
        self.assertEqual(snapshot["readiness"], "READY")
        self.assertIn("metrics", snapshot)
        self.assertFalse(snapshot["external_action_capability"])
        self.assertFalse(snapshot["memory_write"])


if __name__ == "__main__":
    unittest.main()
