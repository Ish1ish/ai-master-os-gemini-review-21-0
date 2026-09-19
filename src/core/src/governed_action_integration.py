"""O45-S46 governed action execution integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional

from .action_execution_hardening import (
    ActionIntent,
    ApprovalRecord,
    ExecutionReceipt,
    GovernanceDecision,
    HardenedActionExecutor,
    build_action_intent,
    evaluate_governance,
)


@dataclass(frozen=True)
class GovernedActionResult:
    status: str
    intent_id: str
    governance_decision: str
    approval_id: Optional[str]
    receipt: ExecutionReceipt
    external_action_executed: bool
    memory_write_executed: bool = False


class GovernedActionCoordinator:
    """Unified decision → intent → governance → executor boundary."""

    def __init__(self, *, allow_external_execution: bool = False) -> None:
        self.executor = HardenedActionExecutor(
            allow_external_execution=allow_external_execution
        )

    def submit(
        self,
        *,
        project_id: str,
        requester_id: str,
        tool: str,
        action: str,
        capability: str,
        idempotency_key: str,
        granted_capabilities: frozenset[str],
        approval: Optional[ApprovalRecord] = None,
        payload: Any = None,
        external_effect: bool = False,
        financial_effect: bool = False,
        destructive_effect: bool = False,
        tool_callable: Optional[Callable[[ActionIntent], Any]] = None,
    ) -> GovernedActionResult:
        intent = build_action_intent(
            project_id=project_id,
            requester_id=requester_id,
            tool=tool,
            action=action,
            capability=capability,
            idempotency_key=idempotency_key,
            payload=payload,
            external_effect=external_effect,
            financial_effect=financial_effect,
            destructive_effect=destructive_effect,
        )
        decision = evaluate_governance(
            intent,
            granted_capabilities=granted_capabilities,
            approval=approval,
        )
        receipt = self.executor.execute(
            intent,
            granted_capabilities=granted_capabilities,
            approval=approval,
            tool=tool_callable,
        )
        return GovernedActionResult(
            status=receipt.status,
            intent_id=intent.intent_id,
            governance_decision=decision.value,
            approval_id=approval.approval_id if approval else None,
            receipt=receipt,
            external_action_executed=receipt.external_action_executed,
            memory_write_executed=False,
        )

    def snapshot(self) -> Mapping[str, Mapping[str, Any]]:
        return self.executor.snapshot()
