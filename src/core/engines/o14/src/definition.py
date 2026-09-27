from core.src.handoff_contracts import semantic_core, compact_semantic_text

class ProductDefinitionBuilder:
    def build(self, strategy, idea, audience="", constraints=None):
        constraints=list(constraints or [])
        model=strategy.get("recommended_model") or {}
        product_handoff = strategy.get("product_handoff") if isinstance(strategy, dict) else None
        idea_text = (product_handoff or {}).get("problem") or (idea.get("problem_statement") if isinstance(idea, dict) else "") or (idea.get("idea") if isinstance(idea, dict) else "")
        idea_text = semantic_core(idea_text) or "validated customer problem"
        opportunity_title = compact_semantic_text((product_handoff or {}).get("opportunity_title") or (idea.get("title") if isinstance(idea, dict) else ""))
        desired_outcome = compact_semantic_text((product_handoff or {}).get("desired_outcome") or (idea.get("desired_outcome") if isinstance(idea, dict) else ""))
        solution_format = compact_semantic_text((product_handoff or {}).get("solution_format") or (idea.get("solution_format") if isinstance(idea, dict) else ""))
        model_name = str(model.get("name") or "").strip()
        product_type_map = {
            "Service / Productized Service": "Productized Service",
            "Digital Product": "Digital Product",
            "Hybrid Product + Service": "Hybrid Product + Service",
        }
        product_type = product_type_map.get(model_name, "Productized Service" if "service" in solution_format.lower() else (model_name or "Focused Business Solution"))
        positioning_link = compact_semantic_text(((strategy.get("positioning") or {}).get("positioning_direction")) or strategy.get("recommendation_reason", ""))
        return {
            "handoff_type":"strategy_to_product",
            "source_engine":"E-04",
            "target_engine":"E-05",
            "object_id":str((strategy.get("product_handoff") or {}).get("object_id") or "STRATEGY-001"),
            "product_name_placeholder":opportunity_title or "Working Product",
            "product_type":product_type,
            "core_problem":idea_text,
            "target_audience":compact_semantic_text(audience) or "defined target audience",
            "core_promise":desired_outcome or "Deliver a focused outcome for the defined problem with the smallest useful product scope.",
            "primary_use_case":solution_format or "Solve the highest-priority customer problem identified by the strategy.",
            "constraints":constraints,
            "positioning_link":positioning_link,
        }
