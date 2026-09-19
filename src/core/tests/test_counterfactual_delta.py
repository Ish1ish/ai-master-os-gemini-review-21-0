import unittest

from src.counterfactual_delta import CounterfactualDelta


class TestCounterfactualDelta(unittest.TestCase):
    def result(self, decision="AUTO_ALLOW", risk="LOW", key="k1", action="draft", approvals=0):
        return {
            "status": "PASS" if decision == "AUTO_ALLOW" else decision,
            "decision": decision, "risk": risk, "side_effects": "NONE",
            "plan_hash": "hash-" + key,
            "actions": [{
                "idempotency_key": key, "action": action, "tool_name": "tool",
                "predicted_decision": decision, "predicted_risk": risk,
                "approval_required": approvals > 0, "execution_allowed": decision != "BLOCK",
                "reason_code": "x"
            }],
            "summary": {"estimated_approvals": approvals}
        }

    def test_unchanged_is_unchanged(self):
        out = CounterfactualDelta.compare(self.result(), self.result())
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["posture"], "UNCHANGED")
        self.assertEqual(out["drivers"], [])

    def test_decision_and_risk_change_is_explained(self):
        out = CounterfactualDelta.compare(self.result(), self.result("REVIEW", "HIGH", "k1", approvals=1))
        self.assertTrue(out["decision_changed"])
        self.assertEqual(out["risk_delta"], 2)
        self.assertIn("overall decision changed", out["explanation"])
        self.assertIn("overall risk changed", out["explanation"])

    def test_added_and_removed_actions_are_detected(self):
        b = self.result()
        c = self.result()
        c["actions"].append({"idempotency_key":"k2","action":"publish","tool_name":"publisher","predicted_decision":"REVIEW","predicted_risk":"HIGH"})
        out = CounterfactualDelta.compare(b, c)
        self.assertEqual(out["added_actions"], ["k2"])
        c["actions"] = [c["actions"][1]]
        out = CounterfactualDelta.compare(b, c)
        self.assertEqual(out["removed_actions"], ["k1"])

    def test_changed_action_is_detected(self):
        b = self.result()
        c = self.result()
        c["actions"][0]["predicted_decision"] = "REVIEW"
        c["actions"][0]["predicted_risk"] = "HIGH"
        out = CounterfactualDelta.compare(b, c)
        self.assertEqual(out["changed_actions"][0]["idempotency_key"], "k1")
        self.assertIn("predicted_decision", out["changed_actions"][0]["changes"])

    def test_side_effectful_inputs_fail_closed(self):
        b = self.result(); c = self.result(); c["side_effects"] = "UNKNOWN"
        out = CounterfactualDelta.compare(b, c)
        self.assertEqual(out["status"], "BLOCK")
        self.assertEqual(out["reason"], "delta_requires_side_effect_free_results")

if __name__ == "__main__":
    unittest.main()
