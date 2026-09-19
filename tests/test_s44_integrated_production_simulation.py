import unittest

from s44_integrated_simulation import run_deterministic_integration

class TestS44IntegratedSimulation(unittest.TestCase):
    def test_authenticated_admission_and_governance_boundary(self):
        r=run_deterministic_integration()
        self.assertTrue(r["authenticated_admission"])
        self.assertTrue(r["governance_boundary"])
    def test_provider_failure_recovery_and_runtime_bounded(self):
        r=run_deterministic_integration()
        self.assertTrue(r["provider_recovery"])
        self.assertTrue(r["runtime_bounded"])
    def test_crash_reconciliation_and_restore_integrity(self):
        r=run_deterministic_integration()
        self.assertTrue(r["crash_reconciled"])
        self.assertTrue(r["restore_integrity"])
    def test_security_and_terminal_integrity(self):
        r=run_deterministic_integration()
        self.assertTrue(r["security_integrity"])
        self.assertTrue(r["terminal_integrity"])
    def test_no_external_consequential_action_or_memory_write(self):
        r=run_deterministic_integration()
        self.assertFalse(r["external_action_executed"])
        self.assertFalse(r["memory_write_executed"])

if __name__ == "__main__":
    unittest.main()
