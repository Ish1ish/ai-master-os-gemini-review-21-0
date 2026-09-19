"""O46-S61 human approval boundary.

Makes consequential action release explicitly dependent on a human approval
record. This layer never performs an external side effect and never grants
implicit approval.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping
import hashlib


class ApprovalState(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ActionRisk(str, Enum):
    BOUNDED = "BOUNDED"
    CONSEQUENTIAL = "CONSEQUENTIAL"


def _fingerprint(*parts: Any) -> str:
    canonical = "|".join(str(p) for p in parts)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


@dataclass(frozen=True)
class ApprovalRequest:
    action_id: str
    action_type: str
    risk: ActionRisk
    summary: str
    state: ApprovalState
    request_fingerprint: str


@dataclass(frozen=True)
class ApprovalDecision:
    action_id: str
    state: ApprovalState
    released: bool
    external_action_executed: bool
    approval_recorded: bool
    auto_approved: bool
    reason: str
    approver_id: str | None = None
    decision_fingerprint: str = ""


class HumanApprovalBoundary:
    """Explicit human gate for consequential actions.

    Bounded actions can pass without approval. Consequential actions always
    enter AWAITING_APPROVAL until an explicit approval or rejection is supplied.
    Approval only releases the action to the next execution layer; this class
    never performs the action itself.
    """

    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}
        self._decisions: dict[str, ApprovalDecision] = {}

    def request(
        self,
        *,
        action_id: str,
        action_type: str,
        risk: ActionRisk,
        summary: str,
    ) -> ApprovalRequest:
        if not action_id or not action_type:
            raise ValueError("action_id and action_type are required")
        fingerprint = _fingerprint(action_id, action_type, risk.value, summary)
        if risk == ActionRisk.BOUNDED:
            request = ApprovalRequest(
                action_id, action_type, risk, summary,
                ApprovalState.NOT_REQUIRED, fingerprint,
            )
        else:
            request = ApprovalRequest(
                action_id, action_type, risk, summary,
                ApprovalState.AWAITING_APPROVAL, fingerprint,
            )
        existing = self._requests.get(action_id)
        if existing is not None:
            return existing
        self._requests[action_id] = request
        return request

    def release_bounded(self, action_id: str) -> ApprovalDecision:
        request = self._requests.get(action_id)
        if request is None:
            return ApprovalDecision(
                action_id, ApprovalState.AWAITING_APPROVAL, False, False,
                False, False, "unknown_action", decision_fingerprint=_fingerprint(action_id, "unknown")
            )
        if request.risk != ActionRisk.BOUNDED:
            return ApprovalDecision(
                action_id, request.state, False, False, False, False,
                "consequential_action_requires_human_approval",
                decision_fingerprint=_fingerprint(action_id, request.state.value),
            )
        decision = ApprovalDecision(
            action_id, ApprovalState.NOT_REQUIRED, True, False, False, False,
            "bounded_action_released_without_human_gate",
            decision_fingerprint=_fingerprint(action_id, "bounded-release"),
        )
        self._decisions[action_id] = decision
        return decision

    def approve(self, *, action_id: str, approver_id: str) -> ApprovalDecision:
        request = self._requests.get(action_id)
        if request is None:
            return ApprovalDecision(
                action_id, ApprovalState.AWAITING_APPROVAL, False, False,
                False, False, "unknown_action", approver_id=approver_id,
                decision_fingerprint=_fingerprint(action_id, approver_id, "unknown")
            )
        if request.risk != ActionRisk.CONSEQUENTIAL:
            return self.release_bounded(action_id)
        if not approver_id.strip():
            return ApprovalDecision(
                action_id, ApprovalState.AWAITING_APPROVAL, False, False,
                False, False, "approver_identity_required", decision_fingerprint=_fingerprint(action_id, "missing-approver")
            )
        existing = self._decisions.get(action_id)
        if existing is not None and existing.state == ApprovalState.APPROVED:
            return existing
        decision = ApprovalDecision(
            action_id, ApprovalState.APPROVED, True, False, True, False,
            "explicit_human_approval_recorded",
            approver_id=approver_id,
            decision_fingerprint=_fingerprint(action_id, approver_id, "approved"),
        )
        self._decisions[action_id] = decision
        return decision

    def reject(self, *, action_id: str, approver_id: str, reason: str = "human_rejected") -> ApprovalDecision:
        request = self._requests.get(action_id)
        if request is None:
            return ApprovalDecision(
                action_id, ApprovalState.AWAITING_APPROVAL, False, False,
                False, False, "unknown_action", approver_id=approver_id,
                decision_fingerprint=_fingerprint(action_id, approver_id, "unknown")
            )
        if request.risk != ActionRisk.CONSEQUENTIAL:
            return self.release_bounded(action_id)
        decision = ApprovalDecision(
            action_id, ApprovalState.REJECTED, False, False, True, False,
            reason or "human_rejected", approver_id=approver_id,
            decision_fingerprint=_fingerprint(action_id, approver_id, "rejected", reason),
        )
        self._decisions[action_id] = decision
        return decision

    def can_release_external(self, action_id: str) -> bool:
        decision = self._decisions.get(action_id)
        return bool(decision and decision.state == ApprovalState.APPROVED and decision.released)

    def snapshot(self) -> Mapping[str, Any]:
        return {
            "request_count": len(self._requests),
            "decision_count": len(self._decisions),
            "approved": sorted(k for k, v in self._decisions.items() if v.state == ApprovalState.APPROVED),
            "rejected": sorted(k for k, v in self._decisions.items() if v.state == ApprovalState.REJECTED),
            "external_action_executed": False,
        }
