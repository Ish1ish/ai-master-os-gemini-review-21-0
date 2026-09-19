import unittest

from unified_runtime.udi_adapter import build_udi_decision_adapter
from unified_runtime.s1 import S1Input, build_s1_runtime
from unified_runtime.o42_adapter import O42EvidenceAdapter


class TestS2O42Integration(unittest.TestCase):
    def _decision_surface(self):
        return {
            "recommendation": "Run a bounded validation experiment",
            "customer": "small businesses",
            "problem": "recurring onboarding friction",
            "desired_outcome": "faster onboarding",
            "opportunity_score": 8.2,
            "strategy_score": 8.0,
            "confidence": 0.8,
            "evidence_boundary": "Current evidence is directional.",
            "validation_experiment": {
                "hypothesis": "Target customers experience recurring onboarding friction strongly enough to justify a focused solution.",
                "sample_size": 10,
                "measure": ["problem_confirmed", "pilot_interest"],
                "thresholds_machine": {
                    "problem_confirmed": {"operator": ">=", "value": 6},
                    "pilot_interest": {"operator": ">=", "value": 3},
                },
                "decision_rule": "GO when both thresholds are met; otherwise REFINE.",
                "external_action_required": False,
            },
        }

    def test_build_preserves_unified_run_identity(self):
        adapter = O42EvidenceAdapter()
        experiment = adapter.build_experiment(
            self._decision_surface(),
            run_id="UR-123",
            project_id="demo",
        )
        self.assertEqual(experiment["run_id"], "UR-123")
        self.assertEqual(experiment["project_id"], "demo")
        self.assertEqual(experiment["experiment_id"], "VAL-UR-123")

    def test_missing_experiment_is_fail_closed(self):
        adapter = O42EvidenceAdapter()
        with self.assertRaisesRegex(ValueError, "decision_surface_has_no_validation_experiment"):
            adapter.build_experiment(
                {"recommendation": "x"},
                run_id="UR-123",
                project_id="demo",
            )

    def test_inconclusive_without_sample_preserves_o42_confidence(self):
        adapter = O42EvidenceAdapter()
        experiment = adapter.build_experiment(
            self._decision_surface(),
            run_id="UR-123",
            project_id="demo",
        )
        result = adapter.evaluate(experiment, {"sample_size": 0})
        self.assertEqual(result["decision"], "INCONCLUSIVE")
        # O42 returns numeric confidence=0.0 for the zero-sample early exit.
        # The S2 bridge preserves the authoritative O42 result rather than
        # rewriting its confidence representation.
        self.assertEqual(result["confidence"], 0.0)

    def test_go_when_thresholds_and_refs_are_met(self):
        adapter = O42EvidenceAdapter()
        result = adapter.evaluate_decision_surface(
            self._decision_surface(),
            run_id="UR-123",
            project_id="demo",
            evidence={
                "sample_size": 10,
                "metrics": {
                    "problem_confirmed": 7,
                    "pilot_interest": 4,
                },
                "evidence_refs": ["EV-001", "EV-002"],
            },
        )
        self.assertEqual(result["evaluation"]["decision"], "GO")
        self.assertTrue(result["evaluation"]["completed"])
        self.assertEqual(result["evaluation"]["next_step"],
                         "Run the smallest bounded pilot or MVP test that delivers the promised outcome.")

    def test_missing_refs_blocks_decision_grade_evidence(self):
        adapter = O42EvidenceAdapter()
        result = adapter.evaluate_decision_surface(
            self._decision_surface(),
            run_id="UR-123",
            project_id="demo",
            evidence={
                "sample_size": 10,
                "metrics": {
                    "problem_confirmed": 9,
                    "pilot_interest": 5,
                },
                "evidence_refs": [],
            },
        )
        self.assertEqual(result["evaluation"]["decision"], "INCONCLUSIVE")
        self.assertEqual(result["evaluation"]["confidence"], "low")

    def test_s1_and_o42_share_run_id(self):
        request = S1Input(project_id="demo", intent="validate onboarding problem")
        s1 = build_s1_runtime(decision=build_udi_decision_adapter())(request)
        surface = self._decision_surface()
        evidence = O42EvidenceAdapter().build_experiment(
            surface,
            run_id=s1.run_id,
            project_id=request.project_id,
        )
        self.assertEqual(evidence["run_id"], s1.run_id)
        self.assertEqual(evidence["project_id"], request.project_id)
        self.assertTrue(s1.trace_id.startswith("TRC-"))


if __name__ == "__main__":
    unittest.main()
