import tempfile
import unittest
from pathlib import Path

from unified_runtime.deployment_validation import UnifiedRuntimeDeploymentValidation


class TestS17DeploymentValidation(unittest.TestCase):
    def _workspace(self):
        return Path(__file__).resolve().parents[1]

    def test_gate_has_explicit_deployment_status(self):
        report = UnifiedRuntimeDeploymentValidation(self._workspace()).run()
        self.assertIn(report["status"], {"READY_FOR_DEPLOYMENT_VALIDATION", "BLOCKED"})

    def test_workspace_missing_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = UnifiedRuntimeDeploymentValidation(Path(tmp) / "missing").run()
        self.assertEqual(report["status"], "BLOCKED")
        self.assertTrue(report["failures"])

    def test_source_and_test_surface_are_explicit(self):
        report = UnifiedRuntimeDeploymentValidation(self._workspace()).run()
        self.assertIn("source_surface_complete", report["checks"])
        self.assertIn("test_surface_complete", report["checks"])

    def test_manifest_is_required(self):
        report = UnifiedRuntimeDeploymentValidation(self._workspace()).run()
        self.assertIn("release_manifest_present", report["checks"])

    def test_local_health_and_readiness_are_exposed(self):
        report = UnifiedRuntimeDeploymentValidation(self._workspace()).run()
        self.assertIn("health", report)
        self.assertIn("readiness", report)
        self.assertIn("local_health_green", report["checks"])
        self.assertIn("local_readiness_green", report["checks"])

    def test_no_external_environment_claim(self):
        report = UnifiedRuntimeDeploymentValidation(self._workspace()).run()
        self.assertFalse(report["posture"]["external_environment_verified"])

    def test_external_action_is_blocked(self):
        report = UnifiedRuntimeDeploymentValidation(self._workspace()).run()
        self.assertFalse(report["posture"]["external_action"])

    def test_memory_write_is_blocked(self):
        report = UnifiedRuntimeDeploymentValidation(self._workspace()).run()
        self.assertFalse(report["posture"]["memory_write"])

    def test_smoke_result_is_explicit(self):
        report = UnifiedRuntimeDeploymentValidation(self._workspace()).run()
        self.assertIn(report["smoke"]["status"], {"PASS", "BLOCKED"})


if __name__ == "__main__":
    unittest.main()
