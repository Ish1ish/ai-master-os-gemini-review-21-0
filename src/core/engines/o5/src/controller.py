from datetime import datetime, timezone
from typing import Dict, Any
from .models import ApprovalRequest
from .store import ApprovalStore
from .risk import classify_risk, requires_approval, build_risk_context

class ApprovalController:
    def __init__(self, store: ApprovalStore | None=None):
        self.store = store or ApprovalStore()

    def request_gate(self, run_id: str, action: str, context: Dict[str, Any],
                     external_effect: bool=False, financial: bool=False,
                     destructive: bool=False, approval_id: str | None=None) -> Dict[str, Any]:
        risk = classify_risk(action, external_effect, financial, destructive)
        if not requires_approval(risk):
            return {
                "status": "NOT_REQUIRED",
                "risk": risk,
                "run_state": "RUNNING",
                "action": action,
            }

        aid = approval_id or f"APR-{run_id}-{len(self.store._items)+1:03d}"
        now = datetime.now(timezone.utc).isoformat()
        req = ApprovalRequest(
            approval_id=aid,
            run_id=run_id,
            action=action,
            risk=risk,
            reason=self._reason(action, risk),
            context=build_risk_context(action, risk, {
                "external_effect": external_effect,
                "financial": financial,
                "destructive": destructive,
                **context,
            }),
            created_at=now,
        )
        self.store.create(req)
        return {
            "status": "PENDING",
            "risk": risk,
            "approval_id": aid,
            "run_state": "AWAITING_APPROVAL",
            "request": req.to_dict(),
        }

    def decide(self, approval_id: str, decision: str, decided_by: str, reason: str) -> Dict[str, Any]:
        req = self.store.decide(approval_id, decision, decided_by, reason)
        next_state = {
            "APPROVED": "RESUME",
            "REJECTED": "CANCELLED",
            "CANCELLED": "CANCELLED",
        }[decision]
        return {
            "status": decision,
            "approval_id": approval_id,
            "run_state": next_state,
            "request": req.to_dict(),
        }

    @staticmethod
    def _reason(action: str, risk: str) -> str:
        return f"Human approval required before consequential action: {action} (risk={risk})."
