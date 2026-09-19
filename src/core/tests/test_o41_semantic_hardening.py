import unittest
from engines.o11.src.research_planner import ResearchPlanner
from engines.o14.src.definition import ProductDefinitionBuilder
from engines.o16.src.topics import TopicGenerator
from src.real_wiring import O23Runtime
from src.providers import fake_model_provider, fake_search_provider

class TestO41SemanticHardening(unittest.TestCase):
    def test_market_queries_are_egypt_first(self):
        plan=ResearchPlanner().build_queries("Find a low-cost AI business","validate in Egypt",["customer_problem","pricing_context"])
        self.assertIn("Egypt",plan["queries"]["customer_problem"])
        self.assertIn("EGP",plan["queries"]["pricing_context"])
        self.assertEqual(plan["research_policy"]["country_priority"],"Egypt-first")
        self.assertIn("local_problem_scan",plan["queries"])
    def test_product_type_is_never_unspecified(self):
        out=ProductDefinitionBuilder().build({"recommended_model":{"name":"Service / Productized Service"},"positioning":{"positioning_direction":"focused validation service"}},{"title":"Validation service","problem_statement":"Need faster validation","desired_outcome":"Make a decision","solution_format":"Service-led validation"},audience="Egyptian founders",constraints=["low cost"])
        self.assertEqual(out["product_type"],"Productized Service")
        self.assertTrue(out["positioning_link"])
    def test_topics_are_publishable(self):
        out=TopicGenerator().generate({"pillars":[{"pillar_id":"P1","name":"Problem Education"}]},problem="Early-stage founders may need faster, simpler market research and validation before committing capital.",audience="Egyptian founders",topics_per_pillar=1)
        self.assertNotIn("may need",out["topics"][0]["topic"].lower())
    def test_runtime_emits_arabic_summary(self):
        runtime=O23Runtime(model_provider=fake_model_provider,search_provider=fake_search_provider)
        try:
            out=runtime.run("JOB-AR-001","PROJ-TEST","Research AI automation for small businesses.",audience="small businesses",goal="validate a lean business opportunity",constraints=["low startup cost"],language="ar")
            self.assertEqual(out["status"],"COMPLETE")
            self.assertEqual(out["arabic_decision_summary"]["language"],"ar")
            self.assertTrue(out["arabic_decision_summary"]["recommendation"])
        finally:
            runtime.close()

if __name__ == "__main__":
    unittest.main()

class TestO412EvidenceHardening(unittest.TestCase):
    def test_generic_global_article_mentioning_egypt_is_not_local(self):
        from engines.o11.src.evidence import build_evidence_pack
        pack = build_evidence_pack([{
            "dimension": "customer_problem",
            "query": "Egypt AI business ideas",
            "results": [{
                "title": "Best AI Business Ideas in 2026 for Egypt",
                "url": "https://example.com/ai-business-ideas",
                "snippet": "A generic worldwide startup ideas list mentions Egypt as one of many markets.",
                "source_type": "web",
            }]
        }])
        self.assertEqual(pack["evidence"][0]["source_role"], "global_context")

    def test_two_local_sources_are_required_for_local_boundary(self):
        from engines.o11.src.analyzer import MarketAnalyzer
        pack = {
            "sources": [{"source_id":"SRC-001"}],
            "evidence": [{"source_id":"SRC-001","claim":"Egyptian pricing EGP","source_role":"local","geographic_relevance":1.0}]
        }
        report = MarketAnalyzer().analyze("Egypt opportunity", {"dimensions":["customer_problem"]}, pack)
        self.assertEqual(report["evidence_boundary"], "global_signal_requires_local_validation")
        self.assertTrue(report["warnings"])

    def test_offer_and_sales_are_named_from_product_identity(self):
        from engines.o18.src.offer import OfferBuilder
        from engines.o19.src.sales_message import SalesMessageBuilder
        product={"product_name_placeholder":"Egyptian Validation Research Service","product_type":"Productized Service","core_promise":"Know what to validate before you build","primary_use_case":"evidence-backed research"}
        offer=OfferBuilder().build(product,{})
        sales=SalesMessageBuilder().build(product,{"positioning":{"positioning_statement":"Focused"}},offer,{"primary_segment":"Egyptian founders"})
        self.assertEqual(offer["offer_name"],"Egyptian Validation Research Service")
        self.assertNotIn("Core Offer", offer["offer_name"])
        self.assertIn("Egyptian Validation Research Service", sales["headline_direction"])
