import tempfile
import unittest

from unified_runtime.final_gate import UnifiedRuntimeFinalAcceptanceGate


class TestS13FinalAcceptanceGate(unittest.TestCase):
    def test_final_gate_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = UnifiedRuntimeFinalAcceptanceGate(tmp).run()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["gate"], "PRODUCTION_GOLDEN_RUN_FINAL_ACCEPTANCE")
        self.assertEqual(report["failures"], [])

    def test_health_and_readiness_are_green(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = UnifiedRuntimeFinalAcceptanceGate(tmp).run()
        self.assertTrue(report["checks"]["health"])
        self.assertTrue(report["checks"]["readiness"])

    def test_canonical_stage_count_is_13(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = UnifiedRuntimeFinalAcceptanceGate(tmp).run()
        self.assertEqual(report["first_run"]["stage_count"], 13)

    def test_replay_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = UnifiedRuntimeFinalAcceptanceGate(tmp).run(run_id="UR-FINAL-002")
        self.assertTrue(report["checks"]["replay"])
        self.assertEqual(report["replay"]["persistence"]["status"], "IDEMPOTENT_REPLAY")

    def test_recovery_is_successful(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = UnifiedRuntimeFinalAcceptanceGate(tmp).run(run_id="UR-FINAL-003")
        self.assertTrue(report["checks"]["recovery"])
        self.assertTrue(report["recovery"]["recovered"])

    def test_metrics_match_acceptance_sequence(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = UnifiedRuntimeFinalAcceptanceGate(tmp).run(run_id="UR-FINAL-004")
        self.assertTrue(report["checks"]["metrics_total"])
        self.assertTrue(report["checks"]["metrics_replayed"])

    def test_no_external_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = UnifiedRuntimeFinalAcceptanceGate(tmp).run(run_id="UR-FINAL-005")
        self.assertFalse(report["external_action"])
        self.assertFalse(report["first_run"]["external_action"])

    def test_no_automatic_memory_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = UnifiedRuntimeFinalAcceptanceGate(tmp).run(run_id="UR-FINAL-006")
        self.assertFalse(report["memory_write"])
        self.assertFalse(report["first_run"]["memory_write"])

    def test_snapshot_remains_operational(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = UnifiedRuntimeFinalAcceptanceGate(tmp).run(run_id="UR-FINAL-007")
        self.assertTrue(report["checks"]["snapshot_healthy"])
        self.assertTrue(report["checks"]["snapshot_ready"])

    def test_gate_explicitly_distinguishes_code_acceptance_from_deployment(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = UnifiedRuntimeFinalAcceptanceGate(tmp).run(run_id="UR-FINAL-008")
        self.assertFalse(report["production_deployment_verified"])
        self.assertIn("real deployment verification", report["note"])

    def test_same_identity_is_repeatable(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = UnifiedRuntimeFinalAcceptanceGate(tmp)
            first = gate.run(run_id="UR-FINAL-009")
            second = gate.run(run_id="UR-FINAL-010")
        self.assertEqual(first["status"], "PASS")
        self.assertEqual(second["status"], "PASS")
        self.assertEqual(first["first_run"]["stage_count"], second["first_run"]["stage_count"])


if __name__ == "__main__":
    unittest.main()
