import unittest

from src.adaptive_decision_context import AdaptiveDecisionContext


def analysis(route="MAINTAIN", findings=None, sample_size=6, confidence="medium"):
    return {
        "analysis_id": "AOA-1",
        "project_id": "P1",
        "analysis_status": "ANALYZED",
        "advisory_route": route,
        "findings": findings or [],
        "sample_size": sample_size,
        "confidence": confidence,
    }


class TestAdaptiveDecisionContext(unittest.TestCase):
    def setUp(self):
        self.adapter = AdaptiveDecisionContext()

    def test_deterministic_context_id(self):
        a = analysis()
        x = self.adapter.build(project_id="P1", analysis=a, candidate_decision="RECOMMEND")
        y = self.adapter.build(project_id="P1", analysis=a, candidate_decision="RECOMMEND")
        self.assertEqual(x["context_id"], y["context_id"])

    def test_cold_start_is_explicit(self):
        x = self.adapter.build(project_id="P1", analysis=None, candidate_decision="RECOMMEND")
        self.assertEqual(x["status"], "COLD_START")
        self.assertEqual(x["advisory_posture"], "COLD_START")
        self.assertEqual(x["advisory_decision"], "RECOMMEND")

    def test_decision_misses_raise_caution(self):
        x = self.adapter.build(
            project_id="P1",
            analysis=analysis("REFINE_DECISION", ["REPEATED_DECISION_MISSES"]),
            candidate_decision="RECOMMEND",
        )
        self.assertEqual(x["advisory_posture"], "ELEVATED_CAUTION")
        self.assertEqual(x["advisory_decision"], "REFINE")

    def test_execution_mismatch_requests_investigation(self):
        x = self.adapter.build(
            project_id="P1",
            analysis=analysis("INVESTIGATE_EXECUTION", ["REPEATED_EXECUTION_MISMATCH"]),
            candidate_decision="RECOMMEND",
        )
        self.assertEqual(x["advisory_posture"], "INVESTIGATE_EXECUTION")
        self.assertEqual(x["advisory_decision"], "REFINE")

    def test_weak_evidence_requests_more_evidence(self):
        x = self.adapter.build(
            project_id="P1",
            analysis=analysis("COLLECT_MORE_EVIDENCE", ["EVIDENCE_COVERAGE_WEAK"]),
            candidate_decision="RECOMMEND",
        )
        self.assertEqual(x["advisory_posture"], "COLLECT_MORE_EVIDENCE")
        self.assertEqual(x["advisory_decision"], "REFINE")

    def test_small_sample_is_not_adaptive(self):
        x = self.adapter.build(
            project_id="P1",
            analysis=analysis("MAINTAIN", [], sample_size=2),
            candidate_decision="RECOMMEND",
        )
        self.assertEqual(x["status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(x["advisory_decision"], "REFINE")

    def test_current_evidence_gate_does_not_lower_safety(self):
        x = self.adapter.build(
            project_id="P1",
            analysis=analysis(),
            candidate_decision="RECOMMEND",
            evidence_sufficient=False,
        )
        self.assertEqual(x["advisory_decision"], "REFINE")

    def test_governance_flag_is_preserved(self):
        x = self.adapter.build(
            project_id="P1",
            analysis=analysis("REFINE_DECISION", ["REPEATED_DECISION_MISSES"]),
            candidate_decision="RECOMMEND",
            governance_required=True,
        )
        self.assertTrue(x["governance_required"])
        self.assertEqual(
            x["governance_authority"],
            "POLICY_AND_GOVERNANCE_REMAIN_AUTHORITATIVE",
        )

    def test_adaptation_never_overrides_hold(self):
        x = self.adapter.build(
            project_id="P1",
            analysis=analysis("REFINE_DECISION", ["REPEATED_DECISION_MISSES"]),
            candidate_decision="HOLD",
        )
        self.assertEqual(x["advisory_decision"], "HOLD")

    def test_project_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            self.adapter.build(
                project_id="P2",
                analysis=analysis(),
                candidate_decision="RECOMMEND",
            )

    def test_no_external_side_effects(self):
        x = self.adapter.build(project_id="P1", analysis=analysis(), candidate_decision="RECOMMEND")
        self.assertFalse(x["external_action_executed"])
        self.assertFalse(x["o43_memory_mutated"])


if __name__ == "__main__":
    unittest.main()
