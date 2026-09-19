import tempfile
import unittest
from pathlib import Path

from unified_runtime.go_live import UnifiedRuntimeGoLiveValidationGate


class TestS15GoLiveValidation(unittest.TestCase):
    def _workspace(self):
        return Path(__file__).resolve().parents[1]

    def test_gate_has_explicit_go_live_status(self):
        report = UnifiedRuntimeGoLiveValidationGate(self._workspace()).run(
            release_run_id="S15-STATUS-001"
        )
        self.assertIn(report["status"], {"READY_FOR_GO_LIVE_VALIDATION", "BLOCKED"})

    def test_no_external_environment_claim(self):
        report = UnifiedRuntimeGoLiveValidationGate(self._workspace()).run(
            release_run_id="S15-SAFETY-001"
        )
        self.assertFalse(report["posture"]["external_environment_verified"])

    def test_external_action_remains_blocked(self):
        report = UnifiedRuntimeGoLiveValidationGate(self._workspace()).run(
            release_run_id="S15-SAFETY-002"
        )
        self.assertFalse(report["posture"]["external_action"])

    def test_memory_write_remains_blocked(self):
        report = UnifiedRuntimeGoLiveValidationGate(self._workspace()).run(
            release_run_id="S15-SAFETY-003"
        )
        self.assertFalse(report["posture"]["memory_write"])

    def test_release_readiness_is_embedded(self):
        report = UnifiedRuntimeGoLiveValidationGate(self._workspace()).run(
            release_run_id="S15-EMBED-001"
        )
        self.assertIn("readiness", report)
        self.assertIn("manifest_fingerprint", report["readiness"])

    def test_deterministic_for_same_release_identity(self):
        # The embedded readiness check is expected to produce the same manifest.
        first = UnifiedRuntimeGoLiveValidationGate(self._workspace()).run(
            release_run_id="S15-DET-001"
        )
        second = UnifiedRuntimeGoLiveValidationGate(self._workspace()).run(
            release_run_id="S15-DET-001"
        )
        self.assertEqual(
            first["readiness"]["manifest_fingerprint"],
            second["readiness"]["manifest_fingerprint"],
        )

    def test_missing_workspace_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = UnifiedRuntimeGoLiveValidationGate(Path(tmp) / "missing").run(
                release_run_id="S15-MISSING-001"
            )
        self.assertEqual(report["status"], "BLOCKED")
        self.assertTrue(report["failures"])


if __name__ == "__main__":
    unittest.main()
