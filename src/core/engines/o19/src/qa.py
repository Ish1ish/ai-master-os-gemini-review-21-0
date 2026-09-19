def validate_sales_output(output):
    issues = []
    if not output.get("sales_message"):
        issues.append({"type":"missing_sales_message"})
    if not output.get("conversion_copy"):
        issues.append({"type":"missing_conversion_copy"})
    if not output.get("qualification"):
        issues.append({"type":"missing_qualification"})
    if not output.get("objections",{}).get("objections"):
        issues.append({"type":"missing_objections"})
    if not output.get("follow_up",{}).get("sequence"):
        issues.append({"type":"missing_followup"})
    if not output.get("expansion",{}).get("expansion_paths"):
        issues.append({"type":"missing_expansion"})

    rules = output.get("conversion_copy",{}).get("copy_rules",[])
    required_phrases = [
        "Avoid fake urgency",
        "guarantees",
        "unsupported statistics",
    ]
    claims_guard = all(any(p.lower() in r.lower() for r in rules) for p in required_phrases)
    if not claims_guard:
        issues.append({"type":"missing_sales_claim_guard"})

    return {
        "qa_id":"O19-SALES-QA",
        "status":"PASS" if not issues else "FAIL",
        "issues":issues,
        "checks":{
            "sales_message":bool(output.get("sales_message")),
            "conversion_copy":bool(output.get("conversion_copy")),
            "qualification":bool(output.get("qualification")),
            "objections":bool(output.get("objections",{}).get("objections")),
            "followup":bool(output.get("follow_up",{}).get("sequence")),
            "expansion":bool(output.get("expansion",{}).get("expansion_paths")),
            "claim_guard":claims_guard,
        }
    }
