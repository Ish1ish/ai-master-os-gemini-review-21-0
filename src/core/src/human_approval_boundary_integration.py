"""O46-S62 human approval boundary integration.

Integrates S60's real-provider governed loop with S61's explicit human
approval boundary. The integrated loop may reach a consequential action,
enter AWAITING_APPROVAL, and wait for an explicit human decision. Approval
only releases the action to a downstream executor; this integration never
performs an external side effect and never writes memory.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .human_approval_boundary import (
    ActionRisk,
    ApprovalDecision,
    ApprovalRequest,
    ApprovalState,
    HumanApprovalBoundary,
)
from .real_provider_governed_autonomous_loop import (
    RealProviderCycle,
    RealProviderGovernedAutonomousLoop,
)


@dataclass(frozen=True)
class IntegratedApprovalResult:
    status: str
    cycles: tuple[RealProviderCycle, ...]
    approval_request: ApprovalRequest
    approval_decision: ApprovalDecision
    released_to_downstream_executor: bool
    external_action_executed: bool
    memory_write_executed: bool
    automatic_approval: bool


class GovernedAutonomousApprovalIntegration:
    """O46 S60 + S61 integration with an explicit approval pause."""

    def __init__(
        self,
        *,
        loop: RealProviderGovernedAutonomousLoop | None = None,
        approval_boundary: HumanApprovalBoundary | None = None,
    ) -> None:
        self.loop = loop or RealProviderGovernedAutonomousLoop()
        self.approval_boundary = approval_boundary or HumanApprovalBoundary()

    @staticmethod
    def _action_id(cycle: RealProviderCycle) -> str:
        return f"O46-CONSEQUENTIAL-{cycle.trace_id}"

    def run_to_approval(self, *, topic: str = "O46 S62 human approval integration") -> IntegratedApprovalResult:
        loop_result = self.loop.run(topic=topic, project_id="O46-S62")
        if loop_result.status != "PASS" or not loop_result.cycles:
            raise RuntimeError("governed_loop_did_not_reach_approval_boundary")

        cycle = loop_result.cycles[-1]
        action_id = self._action_id(cycle)
        request = self.approval_boundary.request(
            action_id=action_id,
            action_type="CONSEQUENTIAL_ACTION_RELEASE",
            risk=ActionRisk.CONSEQUENTIAL,
            summary=(
                "Release the bounded O46 downstream action after the governed "
                "real-provider loop reaches its approval boundary."
            ),
        )
        if request.state != ApprovalState.AWAITING_APPROVAL:
            raise RuntimeError("consequential_action_bypassed_approval_boundary")

        # The actual integrated state remains awaiting approval until an
        # explicit approve()/reject() operation is requested by the caller.
        final_request = self.approval_boundary.request(
            action_id=action_id,
            action_type="CONSEQUENTIAL_ACTION_RELEASE",
            risk=ActionRisk.CONSEQUENTIAL,
            summary=(
                "Release the bounded O46 downstream action after the governed "
                "real-provider loop reaches its approval boundary."
            ),
        )
        return IntegratedApprovalResult(
            status="AWAITING_APPROVAL",
            cycles=loop_result.cycles,
            approval_request=final_request,
            approval_decision=ApprovalDecision(
                action_id=action_id,
                state=ApprovalState.AWAITING_APPROVAL,
                released=False,
                external_action_executed=False,
                approval_recorded=False,
                auto_approved=False,
                reason="explicit_human_decision_required",
            ),
            released_to_downstream_executor=False,
            external_action_executed=False,
            memory_write_executed=False,
            automatic_approval=False,
        )

    def approve(self, action_id: str, approver_id: str) -> ApprovalDecision:
        return self.approval_boundary.approve(action_id=action_id, approver_id=approver_id)

    def reject(self, action_id: str, approver_id: str, reason: str = "human_rejected") -> ApprovalDecision:
        return self.approval_boundary.reject(action_id=action_id, approver_id=approver_id, reason=reason)

    def can_release(self, action_id: str) -> bool:
        return self.approval_boundary.can_release_external(action_id)
