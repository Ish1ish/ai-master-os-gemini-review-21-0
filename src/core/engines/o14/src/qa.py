def validate_product_output(output):
    issues=[]
    if not isinstance(output.get("product_definition"),dict) or not output.get("product_definition"):
        issues.append({"type":"missing_product_definition"})
    if not output.get("architecture",{}).get("modules"):
        issues.append({"type":"missing_product_modules"})
    if not output.get("features",{}).get("features"):
        issues.append({"type":"missing_feature_prioritization"})
    if not output.get("content_architecture",{}).get("product_content_sections"):
        issues.append({"type":"missing_product_content"})
    if not output.get("launch_readiness",{}).get("checks"):
        issues.append({"type":"missing_launch_readiness"})
    return {
        "qa_id":"O14-PRODUCT-QA",
        "status":"PASS" if not issues else "FAIL",
        "issues":issues,
        "checks":{
            "definition":not any(x["type"]=="missing_product_definition" for x in issues),
            "architecture":not any(x["type"]=="missing_product_modules" for x in issues),
            "features":not any(x["type"]=="missing_feature_prioritization" for x in issues),
            "content":not any(x["type"]=="missing_product_content" for x in issues),
            "launch_readiness":not any(x["type"]=="missing_launch_readiness" for x in issues),
        },
    }
