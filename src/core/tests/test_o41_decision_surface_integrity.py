import unittest

from engines.o12.src.validator import IdeaValidator
from engines.o13.src.engine import RealStrategyEngine
from src.localization import build_decision_surface, build_arabic_decision_summary
from src.real_wiring import O23Runtime
from src.providers import fake_model_provider, fake_search_provider


class TestO414DecisionSurfaceIntegrity(unittest.TestCase):
    def test_validation_experiment_has_thresholds_and_rule(self):
        pack={"ranked_ideas":[{
            "idea_id":"IDEA-001", "overall_score":7.4,
            "customer_segment":"Egyptian small businesses",
            "problem_statement":"Recurring manual work",
            "confidence":"medium"
        }]}
        plan=IdeaValidator().build_validation_plan(pack)["idea_validation_plans"][0]["validation_experiment"]
        self.assertEqual(plan["sample_size"],10)
        self.assertIn("success_threshold",plan)
        self.assertIn("decision_rule",plan)
        self.assertFalse(plan["external_action_required"])

    def test_arabic_low_cost_constraint_prefers_service_validation(self):
        idea={"idea":"Focused workflow solution","title":"Focused workflow solution","problem_statement":"Recurring manual work","desired_outcome":"Reduce manual work"}
        market={"source_count":4,"report":{"source_count":4,"evidence_count":8}}
        out=RealStrategyEngine().build(idea,market,constraints=["تكلفة بداية منخفضة ورأس مال محدود"])
        self.assertEqual(out["strategy"]["recommended_model"]["name"],"Service / Productized Service")
        self.assertEqual(out["strategy"]["validation_model"],"Service-led")
        self.assertEqual(out["strategy"]["long_term_product_model"],"Service / Productized Service")

    def test_decision_surface_uses_ranked_idea_and_market_boundary(self):
        result={
            "ideas":{"scores":{"ranked_ideas":[{
                "title":"Workflow automation service", "problem_statement":"Repeated manual work",
                "desired_outcome":"Faster workflow", "customer_segment":"Egyptian SMEs",
                "opportunity_score":7.4, "confidence":"medium"
            }]},"validation":{"idea_validation_plans":[{"validation_experiment":{
                "method":"Interview 10 Egyptian SMEs",
                "success_threshold":{"problem_confirmation":"6/10"},
                "decision_rule":"GO if threshold is met; otherwise refine."
            }}]}},
            "strategy":{"strategy":{"recommended_model":{"name":"Service / Productized Service"}},"scored_models":[{"model":{"name":"Service / Productized Service"},"strategy_score":{"overall_score":7.8}}],"validation_model":"Service-led","long_term_product_model":"Service / Productized Service"},
            "product":{"product_definition":{"core_problem":"Repeated manual work","core_promise":"Faster workflow","target_audience":"Egyptian SMEs"}},
            "market":{"report":{"source_count":30,"evidence_count":30,"local_source_count":11,"local_evidence_count":11,"evidence_boundary":"local_evidence_supported"}}
        }
        surface=build_decision_surface(result)
        self.assertEqual(surface["opportunity_score"],7.4)
        self.assertEqual(surface["strategy_score"],7.8)
        self.assertEqual(surface["evidence_boundary"],"local_evidence_supported")
        self.assertEqual(surface["validation_model"],"Service-led")
        self.assertEqual(surface["validation_experiment"]["method"],"Interview 10 Egyptian SMEs")


    def test_decision_surface_recovers_nested_opportunity_score(self):
        result={
            "ideas": {
                "scores": {"ranked_ideas": [{
                    "idea_id":"IDEA-001", "title":"Ops assistant",
                    "opportunity": {"opportunity_id":"OPP-001", "opportunity_score":6.85},
                    "opportunity_id":"OPP-001", "confidence":"medium"
                }]},
                "opportunity_candidates": [{"opportunity_id":"OPP-001", "opportunity_score":6.85}],
            },
            "strategy": {"strategy":{"recommended_model":{"name":"Digital Product"}},
                        "scored_models":[{"model":{"name":"Digital Product","model_id":"BM-01"},"strategy_score":{"overall_score":7.25}}]},
            "product": {"product_definition": {"target_audience":"Egyptian SMEs"}},
            "market": {"report": {"source_count":2,"evidence_count":12}},
        }
        surface=build_decision_surface(result)
        self.assertEqual(surface["opportunity_score"],6.85)
        self.assertEqual(surface["strategy_score"],7.25)

    def test_strategy_score_matches_normalized_model_name(self):
        result={
            "ideas":{"scores":{"ranked_ideas":[{"title":"Ops assistant","opportunity_score":5.5,"confidence":"medium"}]}},
            "strategy": {"strategy":{"recommended_model":{"name":"Service- / Productized Service"}},
                        "scored_models":[{"model":{"name":"Service / Productized Service","model_id":"BM-02"},"strategy_score":{"overall_score":8.15}}]},
            "product":{"product_definition":{"target_audience":"Egyptian SMEs"}},
            "market":{"report":{"source_count":2,"evidence_count":12}},
        }
        surface=build_decision_surface(result)
        self.assertEqual(surface["strategy_score"],8.15)

    def test_product_context_preserves_selected_strategy_model(self):
        from src.context_firewall import strategy_context_for_product
        strategy={"strategy":{"recommended_model":{"name":"Service / Productized Service"},"validation_model":"Service-led","long_term_product_model":"Service / Productized Service","recommendation_reason":"service-led"},"positioning":{}}
        handoff={"object_id":"STRATEGY-001","problem":"Repeated manual work","source_refs":["SRC-001"]}
        ctx=strategy_context_for_product(strategy,handoff)
        self.assertEqual(ctx["strategy"]["recommended_model"]["name"],"Service / Productized Service")
        self.assertEqual(ctx["strategy"]["validation_model"],"Service-led")
        self.assertEqual(ctx["strategy"]["long_term_product_model"],"Service / Productized Service")

    def test_runtime_exposes_decision_surface_and_complete_arabic_summary(self):
        runtime=O23Runtime(model_provider=fake_model_provider,search_provider=fake_search_provider)
        try:
            out=runtime.run("JOB-O414-001","PROJ-O414","Find a low-cost AI business",audience="Egyptian small businesses",goal="validate an opportunity",constraints=["تكلفة بداية منخفضة","رأس مال محدود"],language="ar")
            self.assertEqual(out["status"],"COMPLETE")
            self.assertIn("decision_surface",out)
            self.assertIsNotNone(out["decision_surface"]["opportunity_score"])
            self.assertIn("validation_model",out["decision_surface"])
            self.assertIn("long_term_product_model",out["decision_surface"])
            self.assertIn("success_threshold",out["arabic_decision_summary"])
        finally:
            runtime.close()

if __name__ == "__main__":
    unittest.main()
