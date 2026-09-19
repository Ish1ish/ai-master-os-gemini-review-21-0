"""O45 Tool / Action Execution Hardening.

Deterministic control layer for moving from a decision/intent to a tool or action
execution request. Consequential external effects remain disabled by default.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from hashlib import sha256
from typing import Any, Callable, Dict, Mapping, Optional


class GovernanceDecision(str, Enum):
    ALLOW = "ALLOW"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class ActionIntent:
    intent_id: str
    project_id: str
    requester_id: str
    tool: str
    action: str
    capability: str
    idempotency_key: str
    external_effect: bool = False
    financial_effect: bool = False
    destructive_effect: bool = False
    payload_hash: str = ""


@dataclass(frozen=True)
class ApprovalRecord:
    approval_id: str
    project_id: str
    requester_id: str
    approver_id: str
    status: str
    capability: str
    reason: str = ""


@dataclass(frozen=True)
class ExecutionReceipt:
    receipt_id: str
    intent_id: str
    project_id: str
    status: str
    governance_decision: str
    approval_id: Optional[str]
    idempotency_key: str
    external_action_executed: bool
    tool_invoked: bool
    result_hash: Optional[str] = None
    failure_reason: Optional[str] = None


def _hash_jsonable(value: Any) -> str:
    raw = repr(value).encode("utf-8", "strict")
    return sha256(raw).hexdigest()


def build_action_intent(
    *,
    project_id: str,
    requester_id: str,
    tool: str,
    action: str,
    capability: str,
    idempotency_key: str,
    payload: Any = None,
    external_effect: bool = False,
    financial_effect: bool = False,
    destructive_effect: bool = False,
) -> ActionIntent:
    if not project_id or not requester_id or not tool or not action or not capability or not idempotency_key:
        raise ValueError("required_action_intent_field_missing")
    intent_seed = "|".join(
        [project_id, requester_id, tool, action, capability, idempotency_key, _hash_jsonable(payload)]
    )
    intent_id = "ACT-" + sha256(intent_seed.encode("utf-8")).hexdigest()[:16].upper()
    return ActionIntent(
        intent_id=intent_id,
        project_id=project_id,
        requester_id=requester_id,
        tool=tool,
        action=action,
        capability=capability,
        idempotency_key=idempotency_key,
        external_effect=external_effect,
        financial_effect=financial_effect,
        destructive_effect=destructive_effect,
        payload_hash=_hash_jsonable(payload),
    )


def evaluate_governance(intent: ActionIntent, *, granted_capabilities: frozenset[str], approval: Optional[ApprovalRecord]) -> GovernanceDecision:
    if intent.capability not in granted_capabilities:
        return GovernanceDecision.BLOCK
    high_impact = intent.external_effect or intent.financial_effect or intent.destructive_effect
    if high_impact:
        if approval is None:
            return GovernanceDecision.APPROVAL_REQUIRED
        if approval.status != "APPROVED":
            return GovernanceDecision.BLOCK
        if approval.project_id != intent.project_id:
            return GovernanceDecision.BLOCK
        if approval.requester_id != intent.requester_id:
            return GovernanceDecision.BLOCK
        if approval.approver_id == intent.requester_id:
            return GovernanceDecision.BLOCK
        if approval.capability != intent.capability:
            return GovernanceDecision.BLOCK
    return GovernanceDecision.ALLOW


class HardenedActionExecutor:
    """Deterministic executor boundary; external effects disabled by default."""

    def __init__(self, *, allow_external_execution: bool = False) -> None:
        self.allow_external_execution = bool(allow_external_execution)
        self._receipts: Dict[str, ExecutionReceipt] = {}
        self._idempotency: Dict[str, str] = {}

    def execute(
        self,
        intent: ActionIntent,
        *,
        granted_capabilities: frozenset[str],
        approval: Optional[ApprovalRecord] = None,
        tool: Optional[Callable[[ActionIntent], Any]] = None,
    ) -> ExecutionReceipt:
        existing_id = self._idempotency.get(intent.idempotency_key)
        if existing_id:
            return self._receipts[existing_id]

        decision = evaluate_governance(intent, granted_capabilities=granted_capabilities, approval=approval)
        receipt_seed = intent.intent_id + ":" + intent.idempotency_key
        receipt_id = "RCPT-" + sha256(receipt_seed.encode("utf-8")).hexdigest()[:16].upper()

        if decision is GovernanceDecision.APPROVAL_REQUIRED:
            receipt = ExecutionReceipt(
                receipt_id=receipt_id,
                intent_id=intent.intent_id,
                project_id=intent.project_id,
                status="AWAITING_APPROVAL",
                governance_decision=decision.value,
                approval_id=approval.approval_id if approval else None,
                idempotency_key=intent.idempotency_key,
                external_action_executed=False,
                tool_invoked=False,
                failure_reason="explicit_approval_required",
            )
            self._store(receipt)
            return receipt

        if decision is GovernanceDecision.BLOCK:
            receipt = ExecutionReceipt(
                receipt_id=receipt_id,
                intent_id=intent.intent_id,
                project_id=intent.project_id,
                status="BLOCKED",
                governance_decision=decision.value,
                approval_id=approval.approval_id if approval else None,
                idempotency_key=intent.idempotency_key,
                external_action_executed=False,
                tool_invoked=False,
                failure_reason="governance_denied",
            )
            self._store(receipt)
            return receipt

        if intent.external_effect and not self.allow_external_execution:
            receipt = ExecutionReceipt(
                receipt_id=receipt_id,
                intent_id=intent.intent_id,
                project_id=intent.project_id,
                status="BLOCKED",
                governance_decision=decision.value,
                approval_id=approval.approval_id if approval else None,
                idempotency_key=intent.idempotency_key,
                external_action_executed=False,
                tool_invoked=False,
                failure_reason="external_execution_disabled",
            )
            self._store(receipt)
            return receipt

        try:
            result = tool(intent) if tool else {"status": "SIMULATED", "intent_id": intent.intent_id}
            receipt = ExecutionReceipt(
                receipt_id=receipt_id,
                intent_id=intent.intent_id,
                project_id=intent.project_id,
                status="EXECUTED",
                governance_decision=decision.value,
                approval_id=approval.approval_id if approval else None,
                idempotency_key=intent.idempotency_key,
                external_action_executed=bool(intent.external_effect and self.allow_external_execution),
                tool_invoked=tool is not None,
                result_hash=_hash_jsonable(result),
            )
        except Exception as exc:
            receipt = ExecutionReceipt(
                receipt_id=receipt_id,
                intent_id=intent.intent_id,
                project_id=intent.project_id,
                status="FAILED",
                governance_decision=decision.value,
                approval_id=approval.approval_id if approval else None,
                idempotency_key=intent.idempotency_key,
                external_action_executed=False,
                tool_invoked=tool is not None,
                failure_reason=type(exc).__name__,
            )
        self._store(receipt)
        return receipt

    def _store(self, receipt: ExecutionReceipt) -> None:
        self._receipts[receipt.receipt_id] = receipt
        self._idempotency[receipt.idempotency_key] = receipt.receipt_id

    def receipt(self, receipt_id: str) -> Optional[ExecutionReceipt]:
        return self._receipts.get(receipt_id)

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        return {rid: asdict(receipt) for rid, receipt in self._receipts.items()}
