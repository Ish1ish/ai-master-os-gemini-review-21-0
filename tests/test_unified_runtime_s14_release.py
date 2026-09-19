import tempfile
import unittest
from pathlib import Path

from unified_runtime.release_readiness import UnifiedRuntimeReleaseReadinessGate


ROOT = Path.cwd()


class TestS14ReleaseReadiness(unittest.TestCase):
    def test_release_gate_is_ready(self):
        report = UnifiedRuntimeReleaseReadinessGate(ROOT).run()
        self.assertEqual(report["status"], "READY_FOR_RELEASE")
        self.assertEqual(report["failures"], [])

    def test_s13_acceptance_is_embedded(self):
        report = UnifiedRuntimeReleaseReadinessGate(ROOT).run(acceptance_run_id="S14-A")
        self.assertTrue(report["checks"]["s13_acceptance_passed"])
        self.assertEqual(report["acceptance"]["status"], "PASS")

    def test_source_surface_is_complete(self):
        report = UnifiedRuntimeReleaseReadinessGate(ROOT).run(acceptance_run_id="S14-B")
        self.assertTrue(report["checks"]["source_surface_complete"])
        self.assertEqual(len(report["source_manifest"]), 15)

    def test_test_surface_is_complete(self):
        report = UnifiedRuntimeReleaseReadinessGate(ROOT).run(acceptance_run_id="S14-C")
        self.assertTrue(report["checks"]["test_surface_complete"])
        self.assertEqual(len(report["source_manifest"]), 15)

    def test_manifest_has_sha256(self):
        report = UnifiedRuntimeReleaseReadinessGate(ROOT).run(acceptance_run_id="S14-D")
        self.assertTrue(report["manifest_fingerprint"])
        self.assertTrue(all(len(item["sha256"]) == 64 for item in report["source_manifest"]))

    def test_manifest_is_repeatable(self):
        first = UnifiedRuntimeReleaseReadinessGate(ROOT).run(acceptance_run_id="S14-E")
        second = UnifiedRuntimeReleaseReadinessGate(ROOT).run(acceptance_run_id="S14-E")
        self.assertEqual(first["manifest_fingerprint"], second["manifest_fingerprint"])

    def test_external_action_is_never_granted(self):
        report = UnifiedRuntimeReleaseReadinessGate(ROOT).run(acceptance_run_id="S14-F")
        self.assertFalse(report["external_action"])
        self.assertFalse(report["acceptance"]["external_action"])

    def test_memory_write_is_never_granted(self):
        report = UnifiedRuntimeReleaseReadinessGate(ROOT).run(acceptance_run_id="S14-G")
        self.assertFalse(report["memory_write"])
        self.assertFalse(report["acceptance"]["memory_write"])

    def test_missing_workspace_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing"
            report = UnifiedRuntimeReleaseReadinessGate(missing).run()
        self.assertEqual(report["status"], "BLOCKED")
        self.assertIn("workspace_exists", report["failures"])


if __name__ == "__main__":
    unittest.main()
