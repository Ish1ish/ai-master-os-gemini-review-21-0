
from .approval_store import ApprovalStore
from .execution_gate import ApprovalExecutionGate

class GovernedExecutor:
    def __init__(self,store): self.store=store; self.gate=ApprovalExecutionGate()
    def execute(self,run_id,action,payload,fn=None,requested_by="system"):
        approvals=[a for a in self.store.for_run(run_id) if a["action"]==action]
        a=approvals[-1] if approvals else None
        if action in self.gate.CONSEQUENTIAL:
            if a is None:
                a=self.store.create(run_id,action,payload,requested_by)
                return {"status":"PENDING","run_state":"AWAITING_APPROVAL","approval_id":a["approval_id"],"approval":a}
            gate=self.gate.evaluate(action,a)
            if gate["status"]!="ALLOW":
                # A resolved rejection/expiry is terminal for this action attempt;
                # do not silently create a fresh approval and bypass the decision.
                return {"status":"BLOCKED","run_state":a["status"],"approval_id":a["approval_id"],"approval":a}
        return {"status":"EXECUTED","run_state":"COMPLETE","approval_id":a["approval_id"] if a else None,"result":fn() if fn else None}
