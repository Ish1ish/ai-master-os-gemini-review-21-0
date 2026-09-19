import unittest

from unified_runtime.o42_adapter import O42EvidenceAdapter
from unified_runtime.evaluation_adapter import UnifiedEvaluationAdapter
from unified_runtime.governance_adapter import UnifiedGovernanceAdapter


class TestS4GovernanceIntegration(unittest.TestCase):
    def _surface(self):
        return {
            "recommendation": "Run bounded validation",
            "customer": "small businesses",
            "problem": "onboarding friction",
            "desired_outcome": "faster onboarding",
            "opportunity_score": 8.2,
            "strategy_score": 8.0,
            "confidence": 0.8,
            "evidence_boundary": "Directional evidence only.",
            "validation_experiment": {
                "hypothesis": "Customers experience onboarding friction.",
                "sample_size": 10,
                "thresholds_machine": {
                    "problem_confirmed": {"operator": ">=", "value": 6},
                    "pilot_interest": {"operator": ">=", "value": 3},
                },
                "external_action_required": False,
            },
        }

    def _evaluation(self, decision="GO", completed=True):
        evidence = {
            "sample_size": 10,
            "metrics": {"problem_confirmed": 7, "pilot_interest": 4},
            "evidence_refs": ["EV-001", "EV-002"],
        }
        o42 = O42EvidenceAdapter().evaluate_decision_surface(
            self._surface(), run_id="UR-001", project_id="demo", evidence=evidence
        )["evaluation"]
        o42["decision"] = decision
        o42["completed"] = completed
        return UnifiedEvaluationAdapter().normalize(o42, run_id="UR-001", project_id="demo")

    def test_go_requires_execution_gate(self):
        result = UnifiedGovernanceAdapter().evaluate(
            self._evaluation("GO"), run_id="UR-001", project_id="demo"
        )
        self.assertEqual(result["status"], "GOVERNED")
        self.assertEqual(result["posture"], "PROCEED_TO_EXECUTION_GATE")
        self.assertFalse(result["approval_required"])
        self.assertFalse(result["external_action_allowed"])
        self.assertFalse(result["external_action_executed"])

    def test_refine_blocks_execution_and_routes_back(self):
        result = UnifiedGovernanceAdapter().evaluate(
            self._evaluation("REFINE"), run_id="UR-001", project_id="demo"
        )
        self.assertEqual(result["posture"], "REFINE_BEFORE_EXECUTION")
        self.assertFalse(result["external_action_allowed"])

    def test_no_go_stops_progression(self):
        result = UnifiedGovernanceAdapter().evaluate(
            self._evaluation("NO-GO"), run_id="UR-001", project_id="demo"
        )
        self.assertEqual(result["posture"], "DO_NOT_PROCEED")
        self.assertFalse(result["external_action_allowed"])

    def test_inconclusive_holds_for_evidence(self):
        result = UnifiedGovernanceAdapter().evaluate(
            self._evaluation("INCONCLUSIVE"), run_id="UR-001", project_id="demo"
        )
        self.assertEqual(result["posture"], "HOLD_FOR_MORE_EVIDENCE")

    def test_incomplete_evaluation_fails_closed(self):
        result = UnifiedGovernanceAdapter().evaluate(
            self._evaluation("GO", completed=False), run_id="UR-001", project_id="demo"
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["posture"], "BLOCK")

    def test_invalid_decision_fails_closed(self):
        result = UnifiedGovernanceAdapter().evaluate(
            {"decision": "UNKNOWN", "completed": True},
            run_id="UR-001", project_id="demo",
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["external_action_allowed"])
        self.assertFalse(result["external_action_executed"])

    def test_identity_and_authoritative_confidence_are_preserved(self):
        evaluation = self._evaluation("GO")
        result = UnifiedGovernanceAdapter().evaluate(
            evaluation, run_id="UR-REAL", project_id="project-real"
        )
        self.assertEqual(result["run_id"], "UR-REAL")
        self.assertEqual(result["project_id"], "project-real")
        self.assertEqual(result["confidence"], evaluation["confidence"])
        self.assertFalse(result["governance_mutation"])

    def test_human_approval_remains_reserved_for_later_consequential_gate(self):
        result = UnifiedGovernanceAdapter().evaluate(
            self._evaluation("GO"), run_id="UR-001", project_id="demo"
        )
        self.assertFalse(result["approval_required"])
        self.assertEqual(result["approval_status"], "NOT_REQUIRED")
        self.assertFalse(result["external_action_allowed"])


if __name__ == "__main__":
    unittest.main()
