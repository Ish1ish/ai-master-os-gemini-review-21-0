import unittest

from src.api import InProcessAPI
from src.service import ApplicationService


class TestCounterfactualPreflightAPI(unittest.TestCase):
    def setUp(self):
        self.service = ApplicationService(db_path=":memory:", experiments_db_path=":memory:")
        self.api = InProcessAPI(self.service)

    def tearDown(self):
        self.service.close()

    def test_preflight_endpoint_contract_is_side_effect_free(self):
        result = self.api.simulate_counterfactual({
            "project_id": "UI-DEMO",
            "requested_by": "operator",
            "context": {"confidence": "high", "evidence_refs": ["E1"], "evidence_boundary": "supported"},
            "actions": [
                {"action": "generate_internal_draft", "tool_name": "draft_tool", "payload": {}, "idempotency_key": "cf-1"},
                {"action": "publish_public_content", "tool_name": "publisher", "payload": {}, "idempotency_key": "cf-2"},
            ],
        })
        self.assertEqual(result["status"], "REVIEW")
        self.assertEqual(result["side_effects"], "NONE")
        self.assertEqual(result["summary"]["estimated_approvals"], 1)
        self.assertEqual(result["actions"][0]["predicted_decision"], "AUTO_ALLOW")
        self.assertEqual(result["actions"][1]["predicted_decision"], "REVIEW")

    def test_invalid_preflight_fails_closed(self):
        result = self.api.simulate_counterfactual({"project_id": "UI-DEMO", "requested_by": "operator"})
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["decision"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
