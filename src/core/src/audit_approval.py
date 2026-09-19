class ApprovalAudit:
    def __init__(self,operator_store):
        self.store=operator_store

    def record_request(self,approval):
        self.store.record(
            approval["requested_by"],
            "approval_requested",
            approval["approval_id"],
            {"run_id":approval["run_id"],"action":approval["action"]},
            status=approval["status"],
        )

    def record_decision(self,approval):
        self.store.record(
            approval.get("decided_by") or "system",
            "approval_decision",
            approval["approval_id"],
            {"run_id":approval["run_id"],"action":approval["action"],"reason":approval.get("decision_reason")},
            status=approval["status"],
        )
