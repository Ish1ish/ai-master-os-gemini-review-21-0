# PATCH_02_O45_UNIFIED_BRIDGE_V8_TEST_ALIGNMENT
# PATCH_02_O45_UNIFIED_BRIDGE_V7_TEST_ALIGNMENT
import unittest

from unified_runtime.learning_adaptation import UnifiedLearningAdaptationAdapter


class TestPatch02V6PendingLearning(unittest.TestCase):
    def test_pending_execution_is_not_treated_as_failure(self):
        adapter = UnifiedLearningAdaptationAdapter()
        outcome = {
            "execution_id": "EXE-V6-1",
            "run_id": "R-V6",
            "project_id": "P-V6",
            "execution_status": "READY",
            "outcome_status": "PENDING",
            "output": {
                "mode": "O45_GOVERNED_SUBMISSION",
                "submission_status": "READY",
                "execution_state": "READY",
            },
            "error": "",
            "external_action_executed": False,
        }
        result = adapter.run(
            outcome,
            strategy_id="S-V6",
            run_id="R-V6",
            project_id="P-V6",
        )
        self.assertEqual(result["status"], "ADAPTATION_READY")
        self.assertEqual(result["adaptation"]["reason"], "execution_pending_waiting_for_terminal_outcome")
        self.assertEqual(result["feedback"]["signal"], "INCONCLUSIVE_SIGNAL")
        self.assertEqual(result["feedback"]["route"], "WAIT_FOR_OUTCOME")
        self.assertEqual(result["learning"]["learning_status"], "NOT_COMMITTED")
        self.assertEqual(result["adaptation"]["recommendation"], "WAIT_FOR_OUTCOME")
        self.assertEqual(result["adaptation"]["reason"], "execution_pending_waiting_for_terminal_outcome")
        self.assertFalse(result["memory_write"])
        self.assertFalse(result["external_action"])

    def test_terminal_success_keeps_existing_learning_contract(self):
        adapter = UnifiedLearningAdaptationAdapter()
        outcome = {
            "execution_id": "EXE-V6-2",
            "run_id": "R-V6-S",
            "project_id": "P-V6",
            "execution_status": "SUCCEEDED",
            "outcome_status": "SUCCESS",
            "output": {"ok": True},
            "error": "",
            "external_action_executed": False,
        }
        result = adapter.run(
            outcome,
            strategy_id="S-V6",
            run_id="R-V6-S",
            project_id="P-V6",
        )
        self.assertEqual(result["status"], "ADAPTATION_READY")
        self.assertEqual(result["feedback"]["signal"], "POSITIVE_STRATEGY_SIGNAL")
        self.assertEqual(result["adaptation"]["recommendation"], "MAINTAIN_STRATEGY")
        self.assertEqual(result["adaptation"]["reason"], "positive_feedback_supports_strategy")


if __name__ == "__main__":
    unittest.main()
