"""O45-S49 persisted outcome -> next-decision loop.

This module adds a traceable persistence boundary around the S47 outcome and S48
execution integration. It deliberately does not write AI memory and does not
perform external actions. The default store is deterministic and in-process;
production storage can be supplied through the same repository contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Mapping, Optional, Protocol

from .execution_outcome_integration import OutcomeAwareGovernedActionCoordinator, OutcomeIntegratedExecutionResult
from .execution_outcome_intelligence import OutcomeIntelligenceResult


@dataclass(frozen=True)
class PersistedOutcomeDecision:
    trace_id: str
    execution_receipt_id: str
    project_id: str
    action_id: str
    outcome_status: str
    decision_feedback: str
    next_decision: str
    learning_signal_id: Optional[str]
    evidence_refs: tuple[str, ...]
    created_at: str
    trace_version: str = "O45-S49-v1"
    memory_write_executed: bool = False


def _trace_id(outcome: OutcomeIntelligenceResult) -> str:
    payload = {
        "receipt": outcome.execution_receipt_id,
        "outcome": outcome.outcome_id,
        "next_decision": outcome.next_decision,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return f"TRACE-{sha256(raw).hexdigest()[:16].upper()}"


class OutcomeDecisionRepository(Protocol):
    def upsert(self, record: PersistedOutcomeDecision) -> PersistedOutcomeDecision: ...
    def get_by_receipt(self, execution_receipt_id: str) -> Optional[PersistedOutcomeDecision]: ...
    def snapshot(self) -> Mapping[str, PersistedOutcomeDecision]: ...


class InMemoryOutcomeDecisionRepository:
    """Deterministic repository for the S49 contract and local verification."""

    def __init__(self) -> None:
        self._records: dict[str, PersistedOutcomeDecision] = {}

    def upsert(self, record: PersistedOutcomeDecision) -> PersistedOutcomeDecision:
        existing = self._records.get(record.execution_receipt_id)
        if existing is not None:
            return existing
        self._records[record.execution_receipt_id] = record
        return record

    def get_by_receipt(self, execution_receipt_id: str) -> Optional[PersistedOutcomeDecision]:
        return self._records.get(execution_receipt_id)

    def snapshot(self) -> Mapping[str, PersistedOutcomeDecision]:
        return dict(self._records)


def persist_outcome(
    outcome: OutcomeIntelligenceResult,
    repository: OutcomeDecisionRepository,
) -> PersistedOutcomeDecision:
    provenance = dict(outcome.provenance or {})
    learning_signal = outcome.learning_signal
    record = PersistedOutcomeDecision(
        trace_id=_trace_id(outcome),
        execution_receipt_id=outcome.execution_receipt_id,
        project_id=str(provenance.get("project_id", "")),
        action_id=str(provenance.get("action_id", "")),
        outcome_status=outcome.status,
        decision_feedback=outcome.decision_feedback,
        next_decision=outcome.next_decision,
        learning_signal_id=learning_signal.signal_id if learning_signal else None,
        evidence_refs=tuple(provenance.get("evidence_refs", ())),
        created_at=datetime.now(timezone.utc).isoformat(),
        memory_write_executed=False,
    )
    return repository.upsert(record)


@dataclass(frozen=True)
class PersistedOutcomeExecutionResult:
    execution: OutcomeIntegratedExecutionResult
    trace: PersistedOutcomeDecision
    next_decision: str
    trace_id: str
    memory_write_executed: bool = False
    external_action_executed: bool = False


class OutcomePersistedGovernedActionCoordinator:
    """S48 coordinator + S47 outcome + S49 persisted decision trace."""

    def __init__(self, coordinator: Any, repository: Optional[OutcomeDecisionRepository] = None,
                 outcome_coordinator: Optional[OutcomeAwareGovernedActionCoordinator] = None) -> None:
        self.repository = repository or InMemoryOutcomeDecisionRepository()
        self.outcome_coordinator = outcome_coordinator or OutcomeAwareGovernedActionCoordinator(coordinator)

    def execute_and_record(self, *args: Any, **kwargs: Any) -> PersistedOutcomeExecutionResult:
        execution = self.outcome_coordinator.execute_and_observe(*args, **kwargs)
        trace = persist_outcome(execution.outcome, self.repository)
        return PersistedOutcomeExecutionResult(
            execution=execution,
            trace=trace,
            next_decision=trace.next_decision,
            trace_id=trace.trace_id,
            memory_write_executed=False,
            external_action_executed=False,
        )

    def get_trace(self, execution_receipt_id: str) -> Optional[PersistedOutcomeDecision]:
        return self.repository.get_by_receipt(execution_receipt_id)
