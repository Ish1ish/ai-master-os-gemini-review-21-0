def validate_brand_output(output):
    issues=[]
    required=[
        ("brand_dna","brand_dna"),
        ("positioning","positioning"),
        ("messaging","messaging"),
        ("voice","voice"),
        ("naming","naming"),
        ("visual_direction","visual_direction"),
    ]
    for key,label in required:
        if not output.get(key):
            issues.append({"type":f"missing_{label}"})

    if output.get("naming",{}).get("availability_check_required") is not True:
        issues.append({"type":"missing_naming_availability_gate"})

    return {
        "qa_id":"O15-BRAND-QA",
        "status":"PASS" if not issues else "FAIL",
        "issues":issues,
        "checks":{k:bool(output.get(k[0])) for k in required},
    }
