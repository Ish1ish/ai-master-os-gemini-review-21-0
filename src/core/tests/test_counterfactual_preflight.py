import unittest

from src.counterfactual_preflight import CounterfactualPreflight


class FakeGovernance:
    def classify(self, action, context):
        if action == "unknown":
            return {"decision": "BLOCK", "risk": "HIGH", "reason_code": "unknown_action", "approval_required": False, "execution_allowed": False}
        return {"decision": "AUTO_ALLOW", "risk": "LOW", "reason_code": "low_risk_high_confidence", "approval_required": False, "execution_allowed": True}


class FakeRegistry:
    def resolve(self, tool_name):
        if tool_name == "missing_tool":
            raise KeyError(tool_name)
        return object()


class TestCounterfactualPreflight(unittest.TestCase):
    def setUp(self):
        self.preflight = CounterfactualPreflight(FakeGovernance(), registry=FakeRegistry())

    def test_pure_autallow_prediction_has_no_side_effect_marker(self):
        result = self.preflight.simulate(
            project_id="P1",
            requested_by="user-1",
            actions=[{
                "action": "generate_internal_draft",
                "tool_name": "draft_tool",
                "payload": {},
                "idempotency_key": "idem-1",
            }],
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["decision"], "AUTO_ALLOW")
        self.assertEqual(result["side_effects"], "NONE")
        self.assertEqual(result["summary"]["action_count"], 1)

    def test_unknown_action_fails_closed_before_execution(self):
        result = self.preflight.simulate(
            project_id="P1",
            requested_by="user-1",
            actions=[{
                "action": "unknown",
                "tool_name": "draft_tool",
                "payload": {},
                "idempotency_key": "idem-2",
            }],
        )
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["summary"]["block"], 1)

    def test_duplicate_idempotency_keys_block_plan(self):
        base = {
            "action": "generate_internal_draft",
            "tool_name": "draft_tool",
            "payload": {},
            "idempotency_key": "same",
        }
        result = self.preflight.simulate(project_id="P1", requested_by="user-1", actions=[base, dict(base)])
        self.assertEqual(result["decision"], "BLOCK")
        self.assertEqual(result["summary"]["block"], 2)
        self.assertIn("duplicate_plan_idempotency_key", result["summary"]["unique_reason_codes"])

    def test_tool_resolution_error_blocks_without_calling_execution(self):
        result = self.preflight.simulate(
            project_id="P1",
            requested_by="user-1",
            actions=[{
                "action": "generate_internal_draft",
                "tool_name": "missing_tool",
                "payload": {},
                "idempotency_key": "idem-3",
            }],
        )
        self.assertEqual(result["decision"], "BLOCK")
        self.assertEqual(result["summary"]["tool_resolution_errors"], 1)
        self.assertEqual(result["actions"][0]["reason_code"], "tool_unavailable")

    def test_invalid_inputs_fail_closed(self):
        result = self.preflight.simulate(project_id="", requested_by="user", actions=[])
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["reason"], "project_id_required")


if __name__ == "__main__":
    unittest.main()
