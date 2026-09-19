def validate_analytics_output(output):
    issues=[]
    for key, kind in [
        ("event_summary","event_summary"),
        ("kpis","kpis"),
        ("funnel","funnel_analysis"),
        ("diagnosis","diagnosis"),
    ]:
        if not output.get(key):
            issues.append({"type":f"missing_{kind}"})
    if "attribution" not in output:
        issues.append({"type":"missing_attribution"})
    if output.get("unsafe_claims"):
        issues.append({"type":"unsupported_analytics_claims","claims":output["unsafe_claims"]})
    return {
        "qa_id":"O21-ANALYTICS-QA",
        "status":"PASS" if not issues else "FAIL",
        "issues":issues,
    }
