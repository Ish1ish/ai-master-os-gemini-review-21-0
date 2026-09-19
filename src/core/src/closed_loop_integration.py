"""O45-S51 full closed-loop integration.

Composes the verified O45 stages into one deterministic local cycle:
S46 governed execution -> S47 outcome intelligence -> S49 persisted trace ->
S50 decision-loop re-entry. Re-entry produces context for the next cycle but
never triggers execution, external effects, memory writes, or production approval.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from .governed_action_integration import GovernedActionCoordinator
from .execution_outcome_persistence import (
    InMemoryOutcomeDecisionRepository,
    OutcomePersistedGovernedActionCoordinator,
    PersistedOutcomeDecision,
)
from .decision_loop_reentry import (
    DecisionLoopContext,
    DecisionLoopReentryCoordinator,
    InMemoryDecisionLoopReentryRepository,
)


class _S46ExecutionAdapter:
    """Expose the existing S46 submit() contract as an execution method."""

    def __init__(self, coordinator: GovernedActionCoordinator) -> None:
        self.coordinator = coordinator

    def execute(
        self, *, requester_id: str, tool: str, action: str, capability: str,
        idempotency_key: str, granted_capabilities: frozenset[str], approval: Any = None,
        payload: Any = None, external_effect: bool = False, financial_effect: bool = False,
        destructive_effect: bool = False, tool_callable: Any = None,
    ) -> Any:
        payload_map = payload if isinstance(payload, Mapping) else {}
        project_id = str(payload_map.get("project_id", "P-S51"))
        return self.coordinator.submit(
            project_id=project_id, requester_id=requester_id, tool=tool, action=action,
            capability=capability, idempotency_key=idempotency_key,
            granted_capabilities=granted_capabilities, approval=approval, payload=payload,
            external_effect=external_effect, financial_effect=financial_effect,
            destructive_effect=destructive_effect, tool_callable=tool_callable,
        )



@dataclass(frozen=True)
class ClosedLoopCycleResult:
    execution_status: str
    execution_receipt_id: str
    outcome_status: str
    decision_feedback: str
    next_decision: str
    trace_id: str
    reentry: DecisionLoopContext
    execution_triggered: bool = False
    external_action_executed: bool = False
    memory_write_executed: bool = False


@dataclass(frozen=True)
class ClosedLoopResult:
    cycles: tuple[ClosedLoopCycleResult, ...]
    final_next_decision: str
    trace_ids: tuple[str, ...]
    reentry_ids: tuple[str, ...]
    execution_triggered: bool = False
    external_action_executed: bool = False
    memory_write_executed: bool = False


class FullClosedLoopCoordinator:
    """Run one or more governed decision/execution/outcome/re-entry cycles."""

    def __init__(self, *, allow_external_execution: bool = False) -> None:
        self.s46 = GovernedActionCoordinator(allow_external_execution=allow_external_execution)
        self.s46_adapter = _S46ExecutionAdapter(self.s46)
        self.trace_repo = InMemoryOutcomeDecisionRepository()
        self.persisted = OutcomePersistedGovernedActionCoordinator(self.s46_adapter, self.trace_repo)
        self.reentry_repo = InMemoryDecisionLoopReentryRepository()
        self.reentry = DecisionLoopReentryCoordinator(self.trace_repo, self.reentry_repo)

    def run_cycle(
        self,
        *,
        project_id: str,
        action_id: str,
        idempotency_key: str,
        payload: Any,
        evidence_refs: tuple[str, ...],
        expected: Any = "COMPLETE",
        actual: Any = "COMPLETE",
    ) -> ClosedLoopCycleResult:
        persisted = self.persisted.execute_and_record(
            project_id=project_id,
            requester_id="operator-01",
            tool="loop-check",
            action="cycle",
            capability="loop:run",
            idempotency_key=idempotency_key,
            granted_capabilities=frozenset({"loop:run"}),
            payload=payload,
            external_effect=False,
            tool_callable=lambda _: {"status": actual, "project_id": project_id, "action_id": action_id},
            action_id=action_id,
            expected=expected,
            actual=actual,
            evidence_refs=evidence_refs,
        )
        execution = persisted.execution.execution_result
        receipt_id = persisted.execution.execution_receipt_id
        reentered = self.reentry.reenter_from_receipt(receipt_id)
        if reentered is None:
            raise RuntimeError("S51 failed to re-enter from persisted S49 trace")
        return ClosedLoopCycleResult(
            execution_status=getattr(execution, "status", execution.get("status") if isinstance(execution, Mapping) else "UNKNOWN"),
            execution_receipt_id=receipt_id,
            outcome_status=persisted.execution.outcome.status,
            decision_feedback=persisted.execution.outcome.decision_feedback,
            next_decision=persisted.next_decision,
            trace_id=persisted.trace_id,
            reentry=reentered.context,
            execution_triggered=False,
            external_action_executed=False,
            memory_write_executed=False,
        )

    def run_two_cycles(self, *, project_id: str = "P-S51") -> ClosedLoopResult:
        first = self.run_cycle(
            project_id=project_id,
            action_id="A-S51-1",
            idempotency_key="S51-CYCLE-1",
            payload={"cycle": 1},
            evidence_refs=("E-S51-1", "E-S51-2"),
        )
        second = self.run_cycle(
            project_id=project_id,
            action_id="A-S51-2",
            idempotency_key="S51-CYCLE-2",
            payload={"cycle": 2, "source_reentry": first.reentry.loop_id},
            evidence_refs=("E-S51-3", "E-S51-4"),
        )
        return ClosedLoopResult(
            cycles=(first, second),
            final_next_decision=second.next_decision,
            trace_ids=(first.trace_id, second.trace_id),
            reentry_ids=(first.reentry.loop_id, second.reentry.loop_id),
            execution_triggered=False,
            external_action_executed=False,
            memory_write_executed=False,
        )

    def trace_snapshot(self) -> Mapping[str, PersistedOutcomeDecision]:
        return self.trace_repo.snapshot()

    def reentry_snapshot(self) -> Mapping[str, DecisionLoopContext]:
        return self.reentry_repo.snapshot()
