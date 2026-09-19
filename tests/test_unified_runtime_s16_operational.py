import tempfile
import unittest
from pathlib import Path

from unified_runtime.operational_acceptance import UnifiedRuntimeOperationalAcceptance


class TestS16OperationalAcceptance(unittest.TestCase):
    def _workspace(self):
        return Path(__file__).resolve().parents[1]

    def test_operational_acceptance_passes(self):
        report = UnifiedRuntimeOperationalAcceptance(self._workspace()).run(
            run_id="S16-ACCEPT-001", repeats=2
        )
        self.assertEqual(report["status"], "OPERATIONALLY_ACCEPTED")

    def test_health_readiness_and_go_live_are_green(self):
        report = UnifiedRuntimeOperationalAcceptance(self._workspace()).run(
            run_id="S16-ACCEPT-002", repeats=1
        )
        self.assertTrue(report["checks"]["health_green"])
        self.assertTrue(report["checks"]["readiness_green"])
        self.assertTrue(report["checks"]["go_live_ready"])

    def test_repeated_cycles_are_bounded_and_successful(self):
        report = UnifiedRuntimeOperationalAcceptance(self._workspace()).run(
            run_id="S16-ACCEPT-003", repeats=3
        )
        self.assertEqual(len(report["cycles"]), 3)
        self.assertTrue(report["checks"]["all_cycles_succeeded"])

    def test_external_action_is_blocked(self):
        report = UnifiedRuntimeOperationalAcceptance(self._workspace()).run(
            run_id="S16-ACCEPT-004", repeats=2
        )
        self.assertTrue(report["checks"]["external_action_blocked"])

    def test_memory_write_is_blocked(self):
        report = UnifiedRuntimeOperationalAcceptance(self._workspace()).run(
            run_id="S16-ACCEPT-005", repeats=2
        )
        self.assertTrue(report["checks"]["memory_write_blocked"])

    def test_invalid_repeat_bound_fails_closed(self):
        report = UnifiedRuntimeOperationalAcceptance(self._workspace()).run(
            run_id="S16-ACCEPT-006", repeats=4
        )
        self.assertEqual(report["status"], "BLOCKED")

    def test_missing_workspace_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = UnifiedRuntimeOperationalAcceptance(Path(tmp) / "missing").run(
                run_id="S16-MISSING-001", repeats=1
            )
        self.assertEqual(report["status"], "BLOCKED")
        self.assertTrue(report["failures"])

    def test_external_environment_is_not_claimed(self):
        report = UnifiedRuntimeOperationalAcceptance(self._workspace()).run(
            run_id="S16-ACCEPT-007", repeats=1
        )
        self.assertFalse(report["external_environment_verified"])

    def test_deterministic_repeatable_structure(self):
        first = UnifiedRuntimeOperationalAcceptance(self._workspace()).run(
            run_id="S16-ACCEPT-008", repeats=1
        )
        second = UnifiedRuntimeOperationalAcceptance(self._workspace()).run(
            run_id="S16-ACCEPT-008", repeats=1
        )
        self.assertEqual(first["status"], second["status"])
        self.assertEqual(first["go_live"]["readiness"]["manifest_fingerprint"], second["go_live"]["readiness"]["manifest_fingerprint"])


if __name__ == "__main__":
    unittest.main()
