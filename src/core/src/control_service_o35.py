
import os
from .approval_store import ApprovalStore
from .governed_executor import GovernedExecutor
from .operator_store import OperatorStore


class O35ControlService:
    def __init__(self, root):
        os.makedirs(root, exist_ok=True)
        self.root = root
        self.approvals = ApprovalStore(os.path.join(root, "approvals.sqlite3"))
        self.operator_store = OperatorStore(os.path.join(root, "operator.sqlite3"))
        self.operator = self.operator_store  # backward-compatible alias
        self.executor = GovernedExecutor(self.approvals)
        self._closed = False

    def execute(self, *args, **kwargs):
        if self._closed:
            raise RuntimeError("O35ControlService is closed")
        return self.executor.execute(*args, **kwargs)

    def execute_consequential(self, run_id, action, payload=None, execute_fn=None, requested_by="system"):
        return self.execute(run_id, action, payload or {}, execute_fn, requested_by=requested_by)

    def request_approval(self, run_id, action, payload, requested_by="system", ttl_seconds=3600):
        if self._closed:
            raise RuntimeError("O35ControlService is closed")
        approval=self.approvals.create(run_id, action, payload, requested_by, ttl_seconds)
        self.operator_store.record(requested_by, "approval_requested", approval["approval_id"], {"run_id":run_id, "action":action}, status="PENDING")
        return {"status":"PENDING", "run_state":"AWAITING_APPROVAL", "approval_id":approval["approval_id"], "approval":approval}

    def get_approval(self, approval_id):
        return self.approvals.get(approval_id)

    def decide(self, approval_id, decision, operator_id, reason=""):
        if self._closed:
            raise RuntimeError("O35ControlService is closed")
        out = self.approvals.decide(approval_id, decision, operator_id, reason)
        if out.get("status") in {"APPROVED", "REJECTED", "EXPIRED"}:
            self.operator_store.record(operator_id, "approval_decision", approval_id, {"reason": reason}, out["status"])
        return out

    def pending(self):
        if self._closed:
            raise RuntimeError("O35ControlService is closed")
        return self.approvals.pending()

    def close(self):
        if self._closed:
            return
        self._closed = True
        errors = []
        for store in (self.operator_store, self.approvals):
            try:
                store.close()
            except Exception as exc:
                errors.append(exc)
        if errors:
            raise errors[0]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
