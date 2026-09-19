def validate_visual_output(output):
    issues=[]

    if not output.get("visual_brief"):
        issues.append({"type":"missing_visual_brief"})
    if not output.get("layout"):
        issues.append({"type":"missing_layout"})
    if not output.get("asset_spec"):
        issues.append({"type":"missing_asset_spec"})
    if not output.get("image_prompt"):
        issues.append({"type":"missing_image_prompt"})
    if not output.get("video_prompt"):
        issues.append({"type":"missing_video_prompt"})

    claim_rule_present = (
        "Do not fabricate" in output.get("image_prompt","")
        and "Do not add unsupported" in " ".join(output.get("asset_spec",{}).get("requirements",[]))
    )
    if not claim_rule_present:
        issues.append({"type":"missing_claim_guard"})

    return {
        "qa_id":"O17-VISUAL-QA",
        "status":"PASS" if not issues else "FAIL",
        "issues":issues,
        "checks":{
            "brief":bool(output.get("visual_brief")),
            "layout":bool(output.get("layout")),
            "assets":bool(output.get("asset_spec")),
            "image_prompt":bool(output.get("image_prompt")),
            "video_prompt":bool(output.get("video_prompt")),
            "claim_guard":claim_rule_present,
        }
    }
