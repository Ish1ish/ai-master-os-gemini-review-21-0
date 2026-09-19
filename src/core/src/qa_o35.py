def validate_o35(output):
    issues=[]
    if output.get("pending_gate_status")!="PENDING":
        issues.append({"type":"missing_pending_gate"})
    if output.get("before_approval_execution")!="BLOCKED":
        issues.append({"type":"pre_approval_execution_not_blocked"})
    if output.get("after_approval_execution")!="EXECUTED":
        issues.append({"type":"post_approval_execution_missing"})
    if output.get("rejected_execution")!="BLOCKED":
        issues.append({"type":"rejected_action_not_blocked"})
    if output.get("audit_status")!="RECORDED":
        issues.append({"type":"approval_audit_missing"})
    return {"qa_id":"O35-APPROVAL-QA","status":"PASS" if not issues else "FAIL","issues":issues}
