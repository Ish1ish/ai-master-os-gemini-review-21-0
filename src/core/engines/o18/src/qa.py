def validate_marketing_output(output):
    issues=[]
    if not output.get("audience",{}).get("primary_segment"):
        issues.append({"type":"missing_audience"})
    if not output.get("offer",{}).get("core_promise"):
        issues.append({"type":"missing_offer"})
    if not output.get("funnel",{}).get("stages"):
        issues.append({"type":"missing_funnel"})
    if not output.get("channels",{}).get("primary_channel_candidates"):
        issues.append({"type":"missing_channels"})
    if not output.get("campaign",{}).get("campaign_structure"):
        issues.append({"type":"missing_campaign"})
    if not output.get("experiments",{}).get("experiments"):
        issues.append({"type":"missing_experiments"})
    if not output.get("metrics",{}).get("core_kpis"):
        issues.append({"type":"missing_metrics"})
    return {
        "qa_id":"O18-MARKETING-QA",
        "status":"PASS" if not issues else "FAIL",
        "issues":issues,
        "checks":{
            "audience":not any(x["type"]=="missing_audience" for x in issues),
            "offer":not any(x["type"]=="missing_offer" for x in issues),
            "funnel":not any(x["type"]=="missing_funnel" for x in issues),
            "channels":not any(x["type"]=="missing_channels" for x in issues),
            "campaign":not any(x["type"]=="missing_campaign" for x in issues),
            "experiments":not any(x["type"]=="missing_experiments" for x in issues),
            "metrics":not any(x["type"]=="missing_metrics" for x in issues),
        },
    }
