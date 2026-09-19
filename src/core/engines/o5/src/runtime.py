from typing import Dict, Any
from .controller import ApprovalController

class O5Runtime:
    def __init__(self):
        self.approvals = ApprovalController()

    def start_action(self, run_id: str, action: str, context: Dict[str, Any],
                     external_effect: bool=False, financial: bool=False,
                     destructive: bool=False) -> Dict[str, Any]:
        return self.approvals.request_gate(
            run_id, action, context,
            external_effect=external_effect,
            financial=financial,
            destructive=destructive,
        )

    def approve(self, approval_id: str, by: str, reason: str="Approved after review") -> Dict[str, Any]:
        return self.approvals.decide(approval_id, "APPROVED", by, reason)

    def reject(self, approval_id: str, by: str, reason: str) -> Dict[str, Any]:
        return self.approvals.decide(approval_id, "REJECTED", by, reason)
