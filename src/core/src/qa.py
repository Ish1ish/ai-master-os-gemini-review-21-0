def validate_deployment(output):
    issues=[]
    if output.get("api_health",{}).get("status")!="OK":
        issues.append({"type":"api_health_failed"})
    if output.get("queue_status")!="COMPLETE":
        issues.append({"type":"queue_execution_failed"})
    if output.get("worker_shutdown",{}).get("status")!="STOPPED":
        issues.append({"type":"worker_shutdown_failed"})
    if output.get("shared_store",{}).get("status")!="SAME_DB":
        issues.append({"type":"shared_store_mismatch"})
    return {
        "qa_id":"O33-DEPLOYMENT-QA",
        "status":"PASS" if not issues else "FAIL",
        "issues":issues,
    }


def validate_deployment_output(output):
    issues=[]
    if output.get("startup_check",{}).get("status")!="PASS":
        issues.append({"type":"startup_check_failed"})
    if output.get("health",{}).get("status")!="HEALTHY":
        issues.append({"type":"health_failed"})
    if output.get("smoke",{}).get("status")!="PASS":
        issues.append({"type":"deployment_smoke_failed"})
    if output.get("shutdown",{}).get("state")!="STOPPED":
        issues.append({"type":"shutdown_failed"})
    return {
        "qa_id":"O31-DEPLOYMENT-QA",
        "status":"PASS" if not issues else "FAIL",
        "issues":issues,
    }


def validate_o34(output):
    issues=[]
    if output.get("status")!="COMPLETE":
        issues.append({"type":"runtime_not_complete"})
    if output.get("readiness",{}).get("status")!="HEALTHY":
        issues.append({"type":"readiness_failed"})
    if output.get("smoke",{}).get("status")!="PASS":
        issues.append({"type":"smoke_failed"})
    if output.get("release_gate",{}).get("status")!="PASS":
        issues.append({"type":"release_gate_blocked"})
    return {
        "qa_id":"O34-FULL-CONTROL-PLANE-QA",
        "status":"PASS" if not issues else "FAIL",
        "issues":issues
    }
