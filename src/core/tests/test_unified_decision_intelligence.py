import unittest

from src.unified_decision_intelligence import UnifiedDecisionIntelligence


class TestUnifiedDecisionIntelligence(unittest.TestCase):
    def candidates(self):
        return [
            {"provider": "A", "tool": "search", "score": 0.80, "cost_usd": 0.01, "latency_ms": 120},
            {"provider": "B", "tool": "search", "score": 0.74, "cost_usd": 0.02, "latency_ms": 80},
        ]

    def test_plan_is_deterministic(self):
        a = UnifiedDecisionIntelligence.plan(
            project_id="p1", context={"tenant": "t1"}, candidates=self.candidates(),
            uncertainty="LOW", reliability="STRONG", resource_pressure="NORMAL",
            latency_posture="NORMAL", cost_posture="WITHIN_BUDGET",
        )
        b = UnifiedDecisionIntelligence.plan(
            project_id="p1", context={"tenant": "t1"}, candidates=self.candidates(),
            uncertainty="LOW", reliability="STRONG", resource_pressure="NORMAL",
            latency_posture="NORMAL", cost_posture="WITHIN_BUDGET",
        )
        self.assertEqual(a["plan_id"], b["plan_id"])
        self.assertEqual(a["routes"], b["routes"])

    def test_missing_candidates_hold(self):
        out = UnifiedDecisionIntelligence.plan(
            project_id="p1", context={}, candidates=[], uncertainty="LOW", reliability="STRONG",
            resource_pressure="NORMAL", latency_posture="NORMAL", cost_posture="WITHIN_BUDGET",
        )
        self.assertEqual(out["status"], "HOLD")
        self.assertIsNone(out["selected_route"])

    def test_high_uncertainty_forces_refine(self):
        out = UnifiedDecisionIntelligence.plan(
            project_id="p1", context={}, candidates=self.candidates(), uncertainty="HIGH", reliability="STRONG",
            resource_pressure="NORMAL", latency_posture="NORMAL", cost_posture="WITHIN_BUDGET",
        )
        self.assertEqual(out["status"], "REFINE")

    def test_unknown_reliability_forces_refine(self):
        out = UnifiedDecisionIntelligence.plan(
            project_id="p1", context={}, candidates=self.candidates(), uncertainty="LOW", reliability="UNKNOWN",
            resource_pressure="NORMAL", latency_posture="NORMAL", cost_posture="WITHIN_BUDGET",
        )
        self.assertEqual(out["status"], "REFINE")

    def test_near_tie_forces_refine(self):
        candidates = [
            {"provider": "A", "tool": "x", "score": 0.80, "cost_usd": 0.01, "latency_ms": 100},
            {"provider": "B", "tool": "x", "score": 0.80, "cost_usd": 0.01, "latency_ms": 100},
        ]
        out = UnifiedDecisionIntelligence.plan(
            project_id="p1", context={}, candidates=candidates, uncertainty="LOW", reliability="STRONG",
            resource_pressure="NORMAL", latency_posture="NORMAL", cost_posture="WITHIN_BUDGET",
        )
        self.assertEqual(out["status"], "REFINE")

    def test_reliability_affects_ranking(self):
        candidates = [
            {"provider": "A", "tool": "x", "score": 0.81, "cost_usd": 0.01, "latency_ms": 100},
            {"provider": "B", "tool": "x", "score": 0.80, "cost_usd": 0.01, "latency_ms": 100},
        ]
        out = UnifiedDecisionIntelligence.plan(
            project_id="p1", context={}, candidates=candidates, uncertainty="LOW", reliability="STRONG",
            resource_pressure="NORMAL", latency_posture="NORMAL", cost_posture="WITHIN_BUDGET",
        )
        self.assertEqual(out["selected_route"]["provider"], "A")

    def test_resource_pressure_penalizes_latency(self):
        candidates = [
            {"provider": "A", "tool": "x", "score": 0.80, "cost_usd": 0.01, "latency_ms": 2000},
            {"provider": "B", "tool": "x", "score": 0.79, "cost_usd": 0.01, "latency_ms": 100},
        ]
        out = UnifiedDecisionIntelligence.plan(
            project_id="p1", context={}, candidates=candidates, uncertainty="LOW", reliability="STRONG",
            resource_pressure="CRITICAL", latency_posture="NORMAL", cost_posture="WITHIN_BUDGET",
        )
        self.assertEqual(out["selected_route"]["provider"], "B")

    def test_cost_pressure_penalizes_expensive_route(self):
        candidates = [
            {"provider": "A", "tool": "x", "score": 0.80, "cost_usd": 2.0, "latency_ms": 100},
            {"provider": "B", "tool": "x", "score": 0.79, "cost_usd": 0.01, "latency_ms": 100},
        ]
        out = UnifiedDecisionIntelligence.plan(
            project_id="p1", context={}, candidates=candidates, uncertainty="LOW", reliability="STRONG",
            resource_pressure="NORMAL", latency_posture="NORMAL", cost_posture="OVER_BUDGET",
        )
        self.assertEqual(out["selected_route"]["provider"], "B")

    def test_invalid_candidates_are_filtered(self):
        out = UnifiedDecisionIntelligence.plan(
            project_id="p1", context={}, candidates=[{}, {"provider": "A"}], uncertainty="LOW", reliability="STRONG",
            resource_pressure="NORMAL", latency_posture="NORMAL", cost_posture="WITHIN_BUDGET",
        )
        self.assertEqual(out["status"], "HOLD")

    def test_governance_never_disabled(self):
        out = UnifiedDecisionIntelligence.plan(
            project_id="p1", context={}, candidates=self.candidates(), uncertainty="LOW", reliability="STRONG",
            resource_pressure="NORMAL", latency_posture="NORMAL", cost_posture="WITHIN_BUDGET",
            governance_required=False,
        )
        self.assertFalse(out["governance_required"])
        self.assertFalse(out["external_action_executed"])
        self.assertEqual(out["governance_authority"], "POLICY_AND_GOVERNANCE_REMAIN_AUTHORITATIVE")

    def test_context_changes_plan_id(self):
        a = UnifiedDecisionIntelligence.plan(
            project_id="p1", context={"tenant": "a"}, candidates=self.candidates(), uncertainty="LOW", reliability="STRONG",
            resource_pressure="NORMAL", latency_posture="NORMAL", cost_posture="WITHIN_BUDGET",
        )
        b = UnifiedDecisionIntelligence.plan(
            project_id="p1", context={"tenant": "b"}, candidates=self.candidates(), uncertainty="LOW", reliability="STRONG",
            resource_pressure="NORMAL", latency_posture="NORMAL", cost_posture="WITHIN_BUDGET",
        )
        self.assertNotEqual(a["plan_id"], b["plan_id"])


if __name__ == "__main__":
    unittest.main()
