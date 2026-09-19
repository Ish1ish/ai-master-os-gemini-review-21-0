import unittest

from unified_runtime.s1 import S1Input, build_s1_runtime
from unified_runtime.udi_adapter import build_udi_decision_adapter


class TestS1UDIIntegration(unittest.TestCase):
    def _request(self):
        return S1Input(
            project_id="demo",
            intent="choose the safest bounded next decision",
            goal="reduce uncertainty without external action",
            audience="small business",
            constraints={"budget": "low", "reversible": True},
            requested_language="en",
            risk_tolerance="standard",
            context_refs=("CTX-001",),
        )

    def test_udi_adapter_returns_real_plan_id_and_status(self):
        result = build_s1_runtime(decision=build_udi_decision_adapter())(self._request())
        decision = result.stages["DECISION"].data

        self.assertEqual(result.next_stage, "EVIDENCE")
        self.assertFalse(result.terminal)
        self.assertEqual(decision["decision_engine"], "UnifiedDecisionIntelligence")
        self.assertTrue(decision["plan_id"].startswith("UDI-"))
        self.assertIn(decision["status"], {"RECOMMEND", "REFINE", "HOLD"})
        self.assertFalse(decision["external_action"])
        self.assertFalse(decision["external_action_executed"])

    def test_same_input_is_deterministic(self):
        adapter = build_udi_decision_adapter()
        request = self._request()

        a = build_s1_runtime(decision=adapter)(request).stages["DECISION"].data
        b = build_s1_runtime(decision=adapter)(request).stages["DECISION"].data

        self.assertEqual(a["plan_id"], b["plan_id"])
        self.assertEqual(a["status"], b["status"])
        self.assertEqual(a["routes"], b["routes"])
        self.assertEqual(a["selected_route"], b["selected_route"])

    def test_route_context_drives_udi_decision(self):
        adapter = build_udi_decision_adapter()

        def route(req, understood):
            return {
                "route_type": "DECISION_INTELLIGENCE",
                "route_mode": "ADVISORY",
                "provider": "provider-a",
                "tool": "tool-a",
                "score": 0.9,
                "uncertainty": "LOW",
                "reliability": "STRONG",
                "resource_pressure": "NORMAL",
                "latency_posture": "NORMAL",
                "cost_posture": "WITHIN_BUDGET",
                "governance_required": True,
                "external_action": False,
            }

        result = build_s1_runtime(route=route, decision=adapter)(self._request())
        decision = result.stages["DECISION"].data

        self.assertEqual(decision["selected_route"]["provider"], "provider-a")
        self.assertEqual(decision["selected_route"]["tool"], "tool-a")
        self.assertEqual(decision["decision_basis"]["uncertainty"], "LOW")
        self.assertEqual(decision["decision_basis"]["reliability"], "STRONG")

    def test_high_uncertainty_refines_instead_of_recommending(self):
        adapter = build_udi_decision_adapter()

        def route(req, understood):
            return {
                "route_type": "DECISION_INTELLIGENCE",
                "route_mode": "ADVISORY",
                "provider": "provider-a",
                "tool": "tool-a",
                "score": 0.9,
                "uncertainty": "HIGH",
                "reliability": "STRONG",
                "resource_pressure": "NORMAL",
                "latency_posture": "NORMAL",
                "cost_posture": "WITHIN_BUDGET",
                "governance_required": True,
                "external_action": False,
            }

        result = build_s1_runtime(route=route, decision=adapter)(self._request())
        self.assertEqual(result.stages["DECISION"].data["status"], "REFINE")

    def test_udi_governance_authority_is_preserved(self):
        result = build_s1_runtime(decision=build_udi_decision_adapter())(self._request())
        decision = result.stages["DECISION"].data

        self.assertEqual(
            decision["governance_authority"],
            "POLICY_AND_GOVERNANCE_REMAIN_AUTHORITATIVE",
        )
        self.assertTrue(decision["governance_required"])


if __name__ == "__main__":
    unittest.main()
