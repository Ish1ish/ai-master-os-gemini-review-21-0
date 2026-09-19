import unittest

from src.handoff_contracts import validate_semantic_handoff
from src.real_wiring import O23Runtime
from src.providers import fake_model_provider, fake_search_provider


class TestCanonicalHandoffChain(unittest.TestCase):
    def test_real_offline_runtime_emits_all_handoffs(self):
        runtime = O23Runtime(model_provider=fake_model_provider, search_provider=fake_search_provider)
        try:
            out = runtime.run(
                "JOB-OFFLINE-HANDOFF-001",
                "PROJ-TEST",
                "Research AI automation for small businesses.",
                audience="small businesses",
                goal="validate a lean business opportunity",
                constraints=["low startup cost", "simple MVP"],
            )
            self.assertEqual(out["status"], "COMPLETE")
            expected = [
                "market_to_idea", "idea_to_strategy", "strategy_to_product",
                "product_to_brand", "brand_to_content", "content_to_visual",
                "visual_to_marketing", "marketing_to_sales", "sales_to_automation",
                "automation_to_analytics", "analytics_to_approval", "approval_to_memory",
                "memory_to_monitoring",
            ]
            self.assertEqual(list(out["handoffs"].keys()), expected)
            for name in expected:
                self.assertEqual(out["handoffs"][name]["qa"]["status"], "PASS", name)
        finally:
            runtime.close()

    def test_raw_evidence_is_rejected_in_semantic_field(self):
        qa = validate_semantic_handoff(
            {
                "handoff_type": "strategy_to_product",
                "source_engine": "E-04",
                "target_engine": "E-05",
                "object_id": "IDEA-001",
                "source_refs": ["SRC-001"],
                "problem": "| Email & CRM | HubSpot | setup friction |",
                "promise": "Focused outcome",
                "confidence": "medium",
            },
            contract="strategy_to_product_v1",
            required_fields=("problem", "promise"),
        )
        self.assertEqual(qa["status"], "FAIL")
        self.assertTrue(any(i["type"] == "raw_evidence_echo" for i in qa["issues"]))

    def test_missing_provenance_is_rejected(self):
        qa = validate_semantic_handoff(
            {
                "handoff_type": "product_to_brand",
                "source_engine": "E-05",
                "target_engine": "E-06",
                "object_id": "PRODUCT-001",
                "problem": "Clean problem",
                "promise": "Clean promise",
                "audience": "Small businesses",
                "confidence": "medium",
            },
            contract="product_to_brand_v1",
            required_fields=("problem", "promise", "audience"),
        )
        self.assertEqual(qa["status"], "FAIL")
        self.assertTrue(any(i["type"] == "missing_source_refs" for i in qa["issues"]))

    def test_unknown_source_reference_is_rejected(self):
        qa = validate_semantic_handoff(
            {
                "handoff_type": "product_to_brand",
                "source_engine": "E-05",
                "target_engine": "E-06",
                "object_id": "PRODUCT-001",
                "source_refs": ["SRC-UNKNOWN"],
                "problem": "Clean problem",
                "promise": "Clean promise",
                "audience": "Small businesses",
                "confidence": "medium",
            },
            contract="product_to_brand_v1",
            required_fields=("problem", "promise", "audience"),
            known_source_refs={"SRC-001"},
        )
        self.assertEqual(qa["status"], "FAIL")
        self.assertTrue(any(i["type"] == "unknown_source_ref" for i in qa["issues"]))


if __name__ == "__main__":
    unittest.main()
