class ApprovalView:
    def __init__(self, audit_provider=None):
        self.audit_provider=audit_provider

    def pending(self):
        if self.audit_provider is None:
            return []
        events=self.audit_provider.for_run if hasattr(self.audit_provider,"for_run") else None
        return {
            "status":"SUPPORTED",
            "note":"Approval views depend on the active audit/control provider.",
        }
