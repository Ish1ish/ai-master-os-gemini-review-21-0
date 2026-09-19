class ApprovalAuthority:
    def can_decide(self, principal, approval):
        roles=set(principal.get("roles", [])) if principal else set()
        if not ({"approver","admin"} & roles):
            return {"status":"DENY","reason":"approver_role_required"}

        # Self-approval prevention for requests created by the same principal.
        if approval and approval.get("requested_by")==principal.get("principal_id"):
            return {"status":"DENY","reason":"self_approval_not_allowed"}

        return {"status":"ALLOW"}
