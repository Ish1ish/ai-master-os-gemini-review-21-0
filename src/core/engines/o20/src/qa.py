def validate_automation_output(output):
    issues=[]

    wf=output.get("workflow",{})
    if not wf.get("workflow_id"):
        issues.append({"type":"missing_workflow_id"})
    if not wf.get("steps"):
        issues.append({"type":"missing_steps"})
    if not output.get("trigger",{}).get("validation"):
        issues.append({"type":"missing_trigger_validation"})
    if not output.get("tool_plan",{}).get("tool_mappings"):
        issues.append({"type":"missing_tool_plan"})
    if not output.get("recovery",{}).get("recovery_policies"):
        issues.append({"type":"missing_recovery"})
    if not output.get("monitoring",{}).get("events"):
        issues.append({"type":"missing_monitoring"})

    return {
        "qa_id":"O20-AUTOMATION-QA",
        "status":"PASS" if not issues else "FAIL",
        "issues":issues,
        "checks":{
            "workflow":bool(wf.get("workflow_id") and wf.get("steps")),
            "trigger":bool(output.get("trigger",{}).get("validation")),
            "tools":bool(output.get("tool_plan",{}).get("tool_mappings")),
            "recovery":bool(output.get("recovery",{}).get("recovery_policies")),
            "monitoring":bool(output.get("monitoring",{}).get("events")),
        },
    }
