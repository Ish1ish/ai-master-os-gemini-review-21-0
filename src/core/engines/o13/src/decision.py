def build_strategy_score(idea, model, market_report, constraints=None):
    constraints=list(constraints or [])
    source_bound=bool(idea.get("source_refs")) and market_report.get("source_count",0)>0
    evidence=8.0 if source_bound else 4.0
    opportunity_specificity=8.0 if idea.get("opportunity_id") and idea.get("problem_statement") and idea.get("desired_outcome") else 4.0
    simplicity=8.0 if model["name"] in {"Service / Productized Service","Digital Product"} else 6.0
    scalability=8.0 if model["name"]=="Digital Product" else 5.5
    learning_speed=8.5 if "Service" in model["name"] else 6.5
    resource_fit=7.5
    low_cost_terms=("low cost", "low-cost", "low startup", "low startup cost", "limited capital", "budget",
                    "تكلفة منخفضة", "تكلفة قليلة", "رأس مال محدود", "رأس مال قليل", "ميزانية محدودة", "بدون تكلفة كبيرة")
    low_cost_constraint=any(any(term in c.lower() for term in low_cost_terms) for c in constraints)
    if low_cost_constraint:
        resource_fit=8.5 if "Service" in model["name"] or "Hybrid" in model["name"] else 6.5
    overall=evidence*.25+opportunity_specificity*.15+simplicity*.15+scalability*.15+learning_speed*.15+resource_fit*.15
    return {
        "scores":{
            "evidence_fit":round(evidence,2),
            "simplicity":round(simplicity,2),
            "scalability":round(scalability,2),
            "learning_speed":round(learning_speed,2),
            "resource_fit":round(resource_fit,2),
            "opportunity_specificity":round(opportunity_specificity,2),
        },
        "overall_score":round(overall,2),
        "boundary":"Strategic score is a prioritization heuristic, not proof of business success."
    }

def select_strategy(scored_models):
    ranked=sorted(scored_models,key=lambda x:(-x["strategy_score"]["overall_score"],x["model"]["model_id"]))
    winner=ranked[0] if ranked else None
    return {
        "ranked_models":ranked,
        "recommended_model":winner["model"] if winner else None,
        "recommendation_reason":"Choose the highest-priority model that best balances evidence, learning speed, resource fit, simplicity, and scalability for the current validation stage." if winner else "No model selected."
    }
