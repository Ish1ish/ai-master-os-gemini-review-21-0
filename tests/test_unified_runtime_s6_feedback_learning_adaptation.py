import unittest

from unified_runtime.learning_adaptation import UnifiedLearningAdaptationAdapter


class TestS6FeedbackLearningAdaptationIntegration(unittest.TestCase):
    def setUp(self):
        self.adapter = UnifiedLearningAdaptationAdapter()
        self.base = {
            "run_id": "UR-001",
            "project_id": "demo",
            "strategy_id": "STRAT-A",
        }

    def test_success_produces_positive_signal_and_maintain(self):
        result = self.adapter.run(
            {"execution_id": "EXE-001", "outcome_status": "SUCCESS"},
            **self.base,
        )
        self.assertEqual(result["status"], "ADAPTATION_READY")
        self.assertEqual(result["feedback"]["signal"], "POSITIVE_STRATEGY_SIGNAL")
        self.assertEqual(result["adaptation"]["recommendation"], "MAINTAIN_STRATEGY")
        self.assertEqual(result["learning"]["learning_status"], "LEARNABLE")
        self.assertEqual(result["learning"]["attribution"], "DECISION")

    def test_failure_routes_to_alternative_hypothesis(self):
        result = self.adapter.run(
            {"execution_id": "EXE-002", "outcome_status": "FAILURE"},
            **self.base,
        )
        self.assertEqual(result["feedback"]["signal"], "NEGATIVE_STRATEGY_SIGNAL")
        self.assertEqual(result["adaptation"]["recommendation"], "EXPLORE_ALTERNATIVE")
        self.assertEqual(result["learning"]["learning_status"], "LEARNABLE")

    def test_blocked_is_not_strategy_evidence(self):
        result = self.adapter.run(
            {"execution_id": "EXE-003", "outcome_status": "BLOCKED"},
            **self.base,
        )
        self.assertEqual(result["feedback"]["signal"], "INCONCLUSIVE_SIGNAL")
        self.assertEqual(result["adaptation"]["recommendation"], "COLLECT_EVIDENCE")
        self.assertEqual(result["learning"]["learning_status"], "NOT_DECISION_DRIVING")
        self.assertEqual(result["learning"]["attribution"], "EXECUTION_BLOCK")

    def test_unknown_outcome_fails_closed(self):
        result = self.adapter.run(
            {"execution_id": "EXE-004", "outcome_status": "UNKNOWN"},
            **self.base,
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["memory_write"])
        self.assertFalse(result["external_action"])

    def test_identity_and_execution_reference_are_preserved(self):
        result = self.adapter.run(
            {"execution_id": "EXE-ABC", "outcome_status": "SUCCESS"},
            strategy_id="STRAT-REAL",
            run_id="UR-REAL",
            project_id="PROJECT-REAL",
        )
        self.assertEqual(result["strategy_id"], "STRAT-REAL")
        self.assertEqual(result["run_id"], "UR-REAL")
        self.assertEqual(result["project_id"], "PROJECT-REAL")
        self.assertEqual(result["source_execution_id"], "EXE-ABC")

    def test_successful_learning_does_not_auto_mutate_memory(self):
        result = self.adapter.run(
            {"execution_id": "EXE-005", "outcome_status": "SUCCESS"},
            **self.base,
        )
        self.assertFalse(result["memory_write"])
        self.assertFalse(result["adaptation"]["o43_mutation"])

    def test_adaptation_is_authoritative_but_not_external(self):
        result = self.adapter.run(
            {"execution_id": "EXE-006", "outcome_status": "FAILURE"},
            **self.base,
        )
        self.assertTrue(result["adaptation"]["authoritative"])
        self.assertFalse(result["adaptation"]["external_action"])
        self.assertFalse(result["external_action"])

    def test_learning_fingerprint_is_deterministic(self):
        payload = {"execution_id": "EXE-007", "outcome_status": "SUCCESS"}
        a = self.adapter.run(payload, **self.base)
        b = self.adapter.run(payload, **self.base)
        self.assertEqual(a["learning_fingerprint"], b["learning_fingerprint"])

    def test_different_strategy_context_changes_learning_fingerprint(self):
        payload = {"execution_id": "EXE-008", "outcome_status": "SUCCESS"}
        a = self.adapter.run(payload, **self.base)
        b = self.adapter.run(
            payload, run_id="UR-001", project_id="demo", strategy_id="STRAT-B"
        )
        self.assertNotEqual(a["learning_fingerprint"], b["learning_fingerprint"])

    def test_no_go_style_non_execution_does_not_get_invented(self):
        result = self.adapter.run(
            {"execution_id": "EXE-009", "outcome_status": "BLOCKED"},
            strategy_id="STRAT-A",
            run_id="UR-002",
            project_id="demo",
        )
        self.assertEqual(result["learning"]["evidence_sufficiency"], "INSUFFICIENT")
        self.assertEqual(result["adaptation"]["recommendation"], "COLLECT_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
