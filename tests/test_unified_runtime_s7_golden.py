import unittest

from unified_runtime.golden_run import GoldenUnifiedRun
from unified_runtime.execution_outcome import UnifiedExecutionOutcomeAdapter
from unified_runtime.learning_adaptation import UnifiedLearningAdaptationAdapter


class TestS7GoldenUnifiedRun(unittest.TestCase):
    def setUp(self):
        self.runner = GoldenUnifiedRun()

    def test_full_golden_run_passes_all_canonical_stages(self):
        result = self.runner.run(
            run_id="UR-GOLDEN-001",
            project_id="demo",
            strategy_id="STRAT-A",
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["stage_count"], 13)
        self.assertEqual(
            [x["stage"] for x in result["trace"]],
            list(GoldenUnifiedRun.STAGES),
        )

    def test_identity_is_preserved_across_every_stage(self):
        result = self.runner.run(
            run_id="UR-GOLDEN-002",
            project_id="project-real",
            strategy_id="STRAT-REAL",
        )
        for entry in result["trace"]:
            self.assertEqual(entry["run_id"], "UR-GOLDEN-002")
            self.assertEqual(entry["project_id"], "project-real")
        self.assertEqual(result["stages"]["NEXT_DECISION"]["strategy_id"], "STRAT-REAL")

    def test_stage_outputs_form_expected_decision_chain(self):
        result = self.runner.run(
            run_id="UR-GOLDEN-003",
            project_id="demo",
            strategy_id="STRAT-A",
        )
        self.assertEqual(result["stages"]["DECISION"]["status"], "RECOMMEND")
        self.assertEqual(result["stages"]["EVALUATION"]["decision"], "GO")
        self.assertEqual(result["stages"]["GOVERNANCE"]["posture"], "PROCEED_TO_EXECUTION_GATE")
        self.assertEqual(result["stages"]["EXECUTION"]["execution_status"], "SUCCEEDED")
        self.assertEqual(result["stages"]["OUTCOME"]["outcome_status"], "SUCCESS")
        self.assertEqual(result["stages"]["FEEDBACK"]["signal"], "POSITIVE_STRATEGY_SIGNAL")
        self.assertEqual(result["stages"]["ADAPTATION"]["recommendation"], "MAINTAIN_STRATEGY")
        self.assertEqual(result["stages"]["NEXT_DECISION"]["route"], "MAINTAIN_STRATEGY")

    def test_golden_run_has_no_external_side_effects(self):
        result = self.runner.run(
            run_id="UR-GOLDEN-004",
            project_id="demo",
            strategy_id="STRAT-A",
        )
        self.assertFalse(result["external_action"])
        self.assertFalse(result["governance_mutation"])
        self.assertFalse(result["memory_write"])
        self.assertFalse(result["stages"]["OUTCOME"]["external_action_executed"])

    def test_golden_run_is_deterministic_for_the_same_identity(self):
        a = self.runner.run(
            run_id="UR-GOLDEN-005",
            project_id="demo",
            strategy_id="STRAT-A",
        )
        b = self.runner.run(
            run_id="UR-GOLDEN-005",
            project_id="demo",
            strategy_id="STRAT-A",
        )
        self.assertEqual(a["stages"]["EXECUTION"]["execution_id"], b["stages"]["EXECUTION"]["execution_id"])
        self.assertEqual(a["stages"]["LEARNING"], b["stages"]["LEARNING"])
        self.assertEqual(a["stages"]["NEXT_DECISION"], b["stages"]["NEXT_DECISION"])

    def test_different_strategy_changes_learning_fingerprint(self):
        a = self.runner.run(
            run_id="UR-GOLDEN-006",
            project_id="demo",
            strategy_id="STRAT-A",
        )
        b = self.runner.run(
            run_id="UR-GOLDEN-006",
            project_id="demo",
            strategy_id="STRAT-B",
        )
        self.assertNotEqual(
            a["stages"]["LEARNING"].get("source_outcome"),
            "UNEXPECTED",
        )
        self.assertNotEqual(
            self.runner.learning.run(
                {"execution_id": "EXE-1", "outcome_status": "SUCCESS"},
                strategy_id="STRAT-A",
                run_id="UR-GOLDEN-006",
                project_id="demo",
            )["learning_fingerprint"],
            self.runner.learning.run(
                {"execution_id": "EXE-1", "outcome_status": "SUCCESS"},
                strategy_id="STRAT-B",
                run_id="UR-GOLDEN-006",
                project_id="demo",
            )["learning_fingerprint"],
        )

    def test_invalid_identity_fails_before_run(self):
        with self.assertRaisesRegex(ValueError, "golden_identity_required"):
            self.runner.run(run_id="", project_id="demo", strategy_id="STRAT-A")

    def test_stage_order_is_canonical(self):
        self.assertEqual(
            GoldenUnifiedRun.STAGES,
            (
                "INTENT", "UNDERSTAND", "ROUTE", "DECISION", "EVIDENCE",
                "EVALUATION", "GOVERNANCE", "EXECUTION", "OUTCOME",
                "FEEDBACK", "LEARNING", "ADAPTATION", "NEXT_DECISION",
            ),
        )

    def test_bounded_executor_failure_would_route_to_adaptation(self):
        execution = UnifiedExecutionOutcomeAdapter().run(
            {"status": "GOVERNED", "posture": "PROCEED_TO_EXECUTION_GATE"},
            run_id="UR-FAIL-001",
            project_id="demo",
            action_key="bounded-validation",
            executor=lambda: {"status": "FAILED", "error": "provider_timeout"},
        )
        learning = UnifiedLearningAdaptationAdapter().run(
            execution,
            strategy_id="STRAT-A",
            run_id="UR-FAIL-001",
            project_id="demo",
        )
        self.assertEqual(execution["outcome_status"], "FAILURE")
        self.assertEqual(learning["feedback"]["signal"], "NEGATIVE_STRATEGY_SIGNAL")
        self.assertEqual(learning["adaptation"]["recommendation"], "EXPLORE_ALTERNATIVE")

    def test_blocked_execution_does_not_blame_strategy(self):
        execution = UnifiedExecutionOutcomeAdapter().run(
            {"status": "GOVERNED", "posture": "REFINE_BEFORE_EXECUTION"},
            run_id="UR-BLOCK-001",
            project_id="demo",
            action_key="bounded-validation",
        )
        learning = UnifiedLearningAdaptationAdapter().run(
            execution,
            strategy_id="STRAT-A",
            run_id="UR-BLOCK-001",
            project_id="demo",
        )
        self.assertEqual(execution["outcome_status"], "BLOCKED")
        self.assertEqual(learning["learning"]["learning_status"], "NOT_DECISION_DRIVING")
        self.assertEqual(learning["adaptation"]["recommendation"], "COLLECT_EVIDENCE")

if __name__ == "__main__":
    unittest.main()
