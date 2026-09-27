from core.src.handoff_contracts import validate_semantic_handoff
def validate_strategy_output(out):
    issues=[]
    if not out.get("business_model_options"): issues.append({"type":"missing_business_model_options"})
    if not out.get("positioning"): issues.append({"type":"missing_positioning"})
    if not out.get("risk_map",{}).get("risks"): issues.append({"type":"missing_risk_map"})
    if not out.get("mvp_plan"): issues.append({"type":"missing_mvp_plan"})
    if not out.get("strategy",{}).get("recommended_model"): issues.append({"type":"missing_recommendation"})
    if not out.get("90_day_plan"): issues.append({"type":"missing_90_day_plan"})
    if out.get("idea_handoff"):
        hq = validate_semantic_handoff(out["idea_handoff"], contract="idea_to_strategy_v1")
        if hq["status"] != "PASS": issues.append({"type":"invalid_idea_handoff", "details": hq["issues"]})
    if out.get("product_handoff"):
        hq = validate_semantic_handoff(out["product_handoff"], contract="strategy_to_product_v1")
        if hq["status"] != "PASS": issues.append({"type":"invalid_product_handoff", "details": hq["issues"]})
    return {
        "qa_id":"O13-STRATEGY-QA",
        "status":"PASS" if not issues else "FAIL",
        "issues":issues,
        "checks":{
            "business_models":bool(out.get("business_model_options")),
            "positioning":bool(out.get("positioning")),
            "risks":bool(out.get("risk_map",{}).get("risks")),
            "mvp":bool(out.get("mvp_plan")),
            "recommendation":bool(out.get("strategy",{}).get("recommended_model")),
            "90_day_plan":bool(out.get("90_day_plan")),
        }
    }
