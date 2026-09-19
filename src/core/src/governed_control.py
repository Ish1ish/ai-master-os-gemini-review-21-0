from .approval_authority import ApprovalAuthority


class GovernedControl:
    def __init__(self, o35_service, authz):
        self.service=o35_service
        self.authz=authz
        self.authority=ApprovalAuthority()

    def decide(self, credentials, approval_id, decision, reason=""):
        auth=self.authz.authenticate(credentials or {})
        if auth["status"]!="AUTHENTICATED":
            return auth
        principal=auth["principal"]
        approval=self.service.get_approval(approval_id)
        if not approval:
            return {"status":"NOT_FOUND","approval_id":approval_id}
        authority=self.authority.can_decide(principal, approval)
        if authority["status"]!="ALLOW":
            return authority
        out=self.service.decide(
            approval_id,
            decision,
            principal["principal_id"],
            reason,
        )
        return out

    def execute(self, credentials, run_id, action, payload, execute_fn=None, requested_by=None):
        auth=self.authz.authenticate(credentials or {})
        if auth["status"]!="AUTHENTICATED":
            return auth
        principal=auth["principal"]

        # Workers must use job:execute for execution.
        if "job:execute" not in principal.get("scopes", []):
            return {"status":"DENY","reason":"job_execute_scope_required"}

        return self.service.execute(
            run_id, action, payload, execute_fn, requested_by=requested_by or principal["principal_id"]
        )
