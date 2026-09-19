import unittest

from src.api import InProcessAPI


class TestO46SemanticMappingRegression(unittest.TestCase):
    def test_audience_and_goal_remain_distinct_end_to_end(self):
        audience = "AUDIENCE_REGRESSION_X"
        goal = "GOAL_REGRESSION_Y"
        api = InProcessAPI()

        queued = api.post_run({
            "project_id": "PROJ-O46-SEMANTIC",
            "request": "Semantic mapping regression check",
            "audience": audience,
            "goal": goal,
            "constraints": ["semantic_mapping_regression"],
            "language": "en",
        })

        self.assertEqual(queued["status"], "QUEUED")
        job_id = queued["job_id"]

        out = api.run_now(job_id)
        self.assertEqual(out["status"], "COMPLETE")
        self.assertEqual(out["audience"], audience)
        self.assertEqual(out["goal"], goal)

        result = out["result"]
        self.assertEqual(result["decision_surface"]["customer"], audience)

        handoffs = result.get("handoffs") or {}
        self.assertEqual(handoffs["idea_to_strategy"]["contract"]["customer_segment"], audience)
        self.assertEqual(handoffs["strategy_to_product"]["contract"]["customer_segment"], audience)
        self.assertEqual(handoffs["product_to_brand"]["contract"]["audience"], audience)
        self.assertEqual(handoffs["brand_to_content"]["contract"]["audience"], audience)
        self.assertEqual(handoffs["marketing_to_sales"]["contract"]["audience"], audience)

        execution_contract = ((result.get("knowledge") or {}).get("execution_contract") or {})
        project_context = execution_contract.get("project_context") or {}
        self.assertEqual(project_context.get("audience"), audience)
        self.assertEqual(project_context.get("goal"), goal)

        prompt_text = (((result.get("prompt") or {}).get("execution_prompt") or {}).get("prompt_text") or "")
        self.assertIn("Objective:\n" + goal, prompt_text)
        self.assertIn("Audience:\n" + audience, prompt_text)

        self.assertNotEqual(out["audience"], out["goal"])
        self.assertNotEqual(result["decision_surface"]["customer"], goal)


if __name__ == "__main__":
    unittest.main()
