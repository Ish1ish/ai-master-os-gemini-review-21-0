"""O45-S50 — deterministic decision-loop re-entry from a persisted outcome trace.

S50 consumes the S49 persisted trace and turns its next_decision into an explicit,
reviewable re-entry context for the next decision cycle. It does not execute an
action, write AI memory, approve production work, or silently mutate state.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Mapping, Optional, Protocol

from .execution_outcome_persistence import OutcomeDecisionRepository, PersistedOutcomeDecision


@dataclass(frozen=True)
class DecisionLoopContext:
    loop_id: str
    source_trace_id: str
    project_id: str
    action_id: str
    outcome_status: str
    next_decision: str
    decision_feedback: str
    evidence_refs: tuple[str, ...]
    source_trace_version: str
    created_at: str
    reentry_version: str = "O45-S50-v1"
    external_action_executed: bool = False
    memory_write_executed: bool = False


def _loop_id(trace: PersistedOutcomeDecision) -> str:
    raw = "|".join((trace.trace_id, trace.execution_receipt_id, trace.next_decision)).encode()
    return f"LOOP-{sha256(raw).hexdigest()[:16].upper()}"


def build_reentry_context(trace: PersistedOutcomeDecision) -> DecisionLoopContext:
    """Convert a persisted S49 trace into a new-cycle decision context."""
    return DecisionLoopContext(
        loop_id=_loop_id(trace),
        source_trace_id=trace.trace_id,
        project_id=trace.project_id,
        action_id=trace.action_id,
        outcome_status=trace.outcome_status,
        next_decision=trace.next_decision,
        decision_feedback=trace.decision_feedback,
        evidence_refs=trace.evidence_refs,
        source_trace_version=trace.trace_version,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


class DecisionLoopReentryRepository(Protocol):
    def upsert(self, context: DecisionLoopContext) -> DecisionLoopContext: ...
    def get(self, loop_id: str) -> Optional[DecisionLoopContext]: ...
    def snapshot(self) -> Mapping[str, DecisionLoopContext]: ...


class InMemoryDecisionLoopReentryRepository:
    def __init__(self) -> None:
        self._records: dict[str, DecisionLoopContext] = {}

    def upsert(self, context: DecisionLoopContext) -> DecisionLoopContext:
        existing = self._records.get(context.loop_id)
        if existing is not None:
            return existing
        self._records[context.loop_id] = context
        return context

    def get(self, loop_id: str) -> Optional[DecisionLoopContext]:
        return self._records.get(loop_id)

    def snapshot(self) -> Mapping[str, DecisionLoopContext]:
        return dict(self._records)


@dataclass(frozen=True)
class DecisionLoopReentryResult:
    context: DecisionLoopContext
    source_trace: PersistedOutcomeDecision
    reentered: bool = True
    execution_triggered: bool = False
    memory_write_executed: bool = False
    external_action_executed: bool = False


class DecisionLoopReentryCoordinator:
    """Resolve an S49 trace into a persisted next-cycle context, once."""

    def __init__(self, outcome_repository: OutcomeDecisionRepository,
                 repository: Optional[DecisionLoopReentryRepository] = None) -> None:
        self.outcome_repository = outcome_repository
        self.repository = repository or InMemoryDecisionLoopReentryRepository()

    def reenter_from_receipt(self, execution_receipt_id: str) -> Optional[DecisionLoopReentryResult]:
        trace = self.outcome_repository.get_by_receipt(execution_receipt_id)
        if trace is None:
            return None
        existing = self.repository.get(_loop_id(trace))
        context = existing or self.repository.upsert(build_reentry_context(trace))
        return DecisionLoopReentryResult(
            context=context,
            source_trace=trace,
            reentered=True,
            execution_triggered=False,
            memory_write_executed=False,
            external_action_executed=False,
        )
