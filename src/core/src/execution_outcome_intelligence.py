"""O45-S47 execution outcome and feedback intelligence."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Mapping, Optional


class OutcomeStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass(frozen=True)
class OutcomeObservation:
    execution_receipt_id: str
    project_id: str
    action_id: str
    expected: Any
    actual: Any
    evidence_refs: tuple[str, ...] = ()
    success_threshold: Optional[float] = None
    observed_score: Optional[float] = None
    notes: str = ""


@dataclass(frozen=True)
class LearningSignal:
    signal_id: str
    outcome_status: str
    statement: str
    evidence_refs: tuple[str, ...]
    next_step: str


@dataclass(frozen=True)
class OutcomeIntelligenceResult:
    status: str
    outcome_id: str
    execution_receipt_id: str
    expected_vs_actual_match: Optional[bool]
    decision_feedback: str
    learning_signal: Optional[LearningSignal]
    next_decision: str
    memory_write_executed: bool = False
    provenance: Mapping[str, Any] = field(default_factory=dict)


def _stable_id(prefix: str, payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()
    return f"{prefix}-{sha256(raw).hexdigest()[:16].upper()}"


def classify_outcome(observation: OutcomeObservation) -> tuple[OutcomeStatus, Optional[bool]]:
    if observation.success_threshold is not None and observation.observed_score is not None:
        if observation.observed_score >= observation.success_threshold:
            return OutcomeStatus.SUCCESS, True
        return OutcomeStatus.FAILURE, False
    if observation.actual is None:
        return OutcomeStatus.INCONCLUSIVE, None
    try:
        return (OutcomeStatus.SUCCESS, True) if observation.actual == observation.expected else (OutcomeStatus.FAILURE, False)
    except Exception:
        return OutcomeStatus.INCONCLUSIVE, None


class ExecutionOutcomeIntelligence:
    """Converts execution receipts into deterministic outcome feedback."""

    def __init__(self) -> None:
        self._outcomes: dict[str, OutcomeIntelligenceResult] = {}

    def record(self, observation: OutcomeObservation) -> OutcomeIntelligenceResult:
        key = observation.execution_receipt_id
        if key in self._outcomes:
            return self._outcomes[key]

        status, matched = classify_outcome(observation)
        if status is OutcomeStatus.SUCCESS:
            feedback = "SUPPORTS_DECISION"
            next_decision = "BOUNDED_NEXT_STEP"
            learning = LearningSignal(
                signal_id=_stable_id("LS", {"receipt": key, "status": status.value}),
                outcome_status=status.value,
                statement="Execution outcome met the declared success criterion.",
                evidence_refs=observation.evidence_refs,
                next_step=next_decision,
            )
        elif status is OutcomeStatus.FAILURE:
            feedback = "CONTRADICTS_DECISION"
            next_decision = "REASSESS_OR_CHANGE"
            learning = LearningSignal(
                signal_id=_stable_id("LS", {"receipt": key, "status": status.value}),
                outcome_status=status.value,
                statement="Execution outcome did not meet the declared success criterion.",
                evidence_refs=observation.evidence_refs,
                next_step=next_decision,
            )
        else:
            feedback = "INSUFFICIENT_EVIDENCE"
            next_decision = "COLLECT_MORE_EVIDENCE"
            learning = None

        result = OutcomeIntelligenceResult(
            status=status.value,
            outcome_id=_stable_id("OUT", {"receipt": key, "project": observation.project_id, "action": observation.action_id}),
            execution_receipt_id=key,
            expected_vs_actual_match=matched,
            decision_feedback=feedback,
            learning_signal=learning,
            next_decision=next_decision,
            memory_write_executed=False,
            provenance={
                "project_id": observation.project_id,
                "action_id": observation.action_id,
                "evidence_refs": list(observation.evidence_refs),
                "outcome_engine_version": "O45-S47-v1",
            },
        )
        self._outcomes[key] = result
        return result

    def snapshot(self) -> Mapping[str, OutcomeIntelligenceResult]:
        return dict(self._outcomes)
