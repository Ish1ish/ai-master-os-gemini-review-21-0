
class ApprovalExecutionGate:
    CONSEQUENTIAL={"publish_public_content","send_external_message","spend_ad_budget","change_price","payment_or_refund","delete_or_modify_critical_data","activate_integration"}
    def evaluate(self,action,approval):
        if action not in self.CONSEQUENTIAL:return {"status":"ALLOW","reason":"non_consequential"}
        if not approval:return {"status":"BLOCKED","reason":"approval_required"}
        return {"status":"ALLOW","reason":"approved"} if approval.get("status")=="APPROVED" else {"status":"BLOCKED","reason":str(approval.get("status","UNRESOLVED")).lower()}
