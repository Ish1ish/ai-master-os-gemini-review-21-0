import unittest

from core.src.real_wiring import _build_execution_outcome_contract


class O48ConsequentialActionOutcomeContractTests(unittest.TestCase):
    def test_pending_approval_is_explicitly_awaiting(self):
        result = _build_execution_outcome_contract({"status": "PENDING", "approval_id": "A1"})
        self.assertEqual(result["execution_status"], "AWAITING_APPROVAL")
        self.assertEqual(result["approval_status"], "PENDING")
        self.assertFalse(result["external_action_executed"])

    def test_released_approval_is_not_reported_as_executed(self):
        result = _build_execution_outcome_contract({"status": "APPROVED", "approval_id": "A1"})
        self.assertEqual(result["execution_status"], "RELEASED")
        self.assertFalse(result["external_action_executed"])

    def test_rejected_approval_is_explicit(self):
        result = _build_execution_outcome_contract({"status": "REJECTED", "approval_id": "A1"})
        self.assertEqual(result["execution_status"], "REJECTED")
        self.assertFalse(result["external_action_executed"])


if __name__ == "__main__":
    unittest.main()
