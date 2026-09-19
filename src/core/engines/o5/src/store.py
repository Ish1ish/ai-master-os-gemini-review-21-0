from typing import Dict
from .models import ApprovalRequest

class ApprovalStore:
    def __init__(self):
        self._items: Dict[str, ApprovalRequest] = {}

    def create(self, request: ApprovalRequest) -> ApprovalRequest:
        if request.approval_id in self._items:
            raise ValueError("approval_id already exists")
        self._items[request.approval_id] = request
        return request

    def get(self, approval_id: str) -> ApprovalRequest | None:
        return self._items.get(approval_id)

    def decide(self, approval_id: str, status: str, decision_by: str, reason: str) -> ApprovalRequest:
        item = self.get(approval_id)
        if item is None:
            raise KeyError("unknown approval_id")
        if item.status != "PENDING":
            raise ValueError("approval is no longer pending")
        if status not in {"APPROVED","REJECTED","CANCELLED"}:
            raise ValueError("invalid approval status")
        item.status = status
        item.decision_by = decision_by
        item.decision_reason = reason
        return item

    def list_pending(self):
        return [x for x in self._items.values() if x.status == "PENDING"]
