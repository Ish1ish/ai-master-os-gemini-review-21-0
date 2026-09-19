def validate_content_output(output):
    issues=[]

    if not output.get("pillars",{}).get("pillars"):
        issues.append({"type":"missing_pillars"})

    if not output.get("topics",{}).get("topics"):
        issues.append({"type":"missing_topics"})

    if not output.get("formats",{}).get("format_plan"):
        issues.append({"type":"missing_formats"})

    if not output.get("hooks"):
        issues.append({"type":"missing_hooks"})

    if not output.get("captions"):
        issues.append({"type":"missing_captions"})

    if not output.get("repurposing"):
        issues.append({"type":"missing_repurposing"})

    return {
        "qa_id":"O16-CONTENT-QA",
        "status":"PASS" if not issues else "FAIL",
        "issues":issues,
        "checks":{
            "pillars":bool(output.get("pillars",{}).get("pillars")),
            "topics":bool(output.get("topics",{}).get("topics")),
            "formats":bool(output.get("formats",{}).get("format_plan")),
            "hooks":bool(output.get("hooks")),
            "captions":bool(output.get("captions")),
            "repurposing":bool(output.get("repurposing")),
        },
    }
