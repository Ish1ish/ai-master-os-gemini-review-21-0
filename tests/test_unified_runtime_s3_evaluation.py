import unittest

from unified_runtime.o42_adapter import O42EvidenceAdapter
from unified_runtime.evaluation_adapter import UnifiedEvaluationAdapter


class TestS3EvaluationIntegration(unittest.TestCase):
    def _surface(self):
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
                "thresholds_machine": {
                    "problem_confirmed": {"operator": ">=", "value": 6},
                    "pilot_interest": {"operator": ">=", "value": 3},
                },
                "external_action_required": False,
            },
        }

    def _evaluated_o42(self, decision="GO"):
        evaluation = O42EvidenceAdapter().evaluate_decision_surface(
            self._surface(),
            run_id="UR-001",
            project_id="demo",
            evidence=(
                {
                    "sample_size": 10,
                    "metrics": {"problem_confirmed": 7, "pilot_interest": 4},
                    "evidence_refs": ["EV-001", "EV-002"],
                }
                if decision == "GO"
                else {
                    "sample_size": 10,
                    "metrics": {"problem_confirmed": 2, "pilot_interest": 1},
                    "evidence_refs": ["EV-001"],
                }
            ),
        )
        return evaluation["evaluation"]

    def test_go_normalizes_to_evaluation_stage(self):
        result = UnifiedEvaluationAdapter().normalize(
            self._evaluated_o42("GO"),
            run_id="UR-001",
            project_id="demo",
        )
        self.assertEqual(result["status"], "EVALUATED")
        self.assertEqual(result["decision"], "GO")
        self.assertEqual(result["run_id"], "UR-001")
        self.assertEqual(result["project_id"], "demo")
        self.assertEqual(result["evidence_refs"], ["EV-001", "EV-002"])
        self.assertFalse(result["external_action_executed"])
        self.assertFalse(result["governance_mutation"])

    def test_refine_preserves_authoritative_o42_decision(self):
        o42 = self._evaluated_o42("REFINE")
        self.assertEqual(o42["decision"], "REFINE")
        result = UnifiedEvaluationAdapter().normalize(
            o42,
            run_id="UR-001",
            project_id="demo",
        )
        self.assertEqual(result["decision"], "REFINE")
        self.assertEqual(result["learning"], o42["learning"])

    def test_inconclusive_preserves_numeric_o42_confidence(self):
        o42 = O42EvidenceAdapter().evaluate_decision_surface(
            self._surface(),
            run_id="UR-001",
            project_id="demo",
            evidence={"sample_size": 0},
        )["evaluation"]
        result = UnifiedEvaluationAdapter().normalize(
            o42,
            run_id="UR-001",
            project_id="demo",
        )
        self.assertEqual(result["decision"], "INCONCLUSIVE")
        self.assertEqual(result["confidence"], 0.0)

    def test_no_go_is_supported(self):
        o42 = dict(self._evaluated_o42("REFINE"))
        o42["decision"] = "NO-GO"
        result = UnifiedEvaluationAdapter().normalize(
            o42,
            run_id="UR-001",
            project_id="demo",
        )
        self.assertEqual(result["decision"], "NO-GO")

    def test_invalid_decision_fails_closed(self):
        o42 = dict(self._evaluated_o42("GO"))
        o42["decision"] = "UNKNOWN"
        with self.assertRaisesRegex(ValueError, "invalid_o42_decision"):
            UnifiedEvaluationAdapter().normalize(
                o42,
                run_id="UR-001",
                project_id="demo",
            )

    def test_missing_required_field_fails_closed(self):
        o42 = dict(self._evaluated_o42("GO"))
        del o42["next_step"]
        with self.assertRaisesRegex(ValueError, "o42_result_missing_keys"):
            UnifiedEvaluationAdapter().normalize(
                o42,
                run_id="UR-001",
                project_id="demo",
            )

    def test_identity_is_not_invented(self):
        o42 = self._evaluated_o42("GO")
        result = UnifiedEvaluationAdapter().normalize(
            o42,
            run_id="UR-REAL",
            project_id="project-real",
        )
        self.assertEqual(result["run_id"], "UR-REAL")
        self.assertEqual(result["project_id"], "project-real")

if __name__ == "__main__":
    unittest.main()
