"""O45-S48 integration between GovernedActionCoordinator (S46) and S47 outcome intelligence.

The adapter composes the existing S46 coordinator. It never enables external execution and
never writes memory. The caller supplies the declared expected outcome plus observed actual
outcome/evidence after the S46 execution attempt completes.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Optional

from .execution_outcome_intelligence import (
    ExecutionOutcomeIntelligence,
    OutcomeIntelligenceResult,
    OutcomeObservation,
)


@dataclass(frozen=True)
class OutcomeIntegratedExecutionResult:
    execution_result: Any
    outcome: OutcomeIntelligenceResult
    execution_receipt_id: str
    integration_version: str = "O45-S48-v1"
    external_action_executed: bool = False
    memory_write_executed: bool = False


def _stable_receipt_id(project_id: str, action_id: str, execution_result: Any) -> str:
    if isinstance(execution_result, Mapping):
        for key in ("execution_receipt_id", "receipt_id", "idempotency_receipt_id", "receipt"):
            value = execution_result.get(key)
            if value:
                return str(value)
    for key in ("execution_receipt_id", "receipt_id", "idempotency_receipt_id", "receipt"):
        value = getattr(execution_result, key, None)
        if value:
            return str(value)
    payload = {"project_id": project_id, "action_id": action_id, "execution_result": execution_result}
    digest = sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()[:16].upper()
    return f"S46-FALLBACK-{digest}"


def _resolve_execution_method(coordinator: Any, explicit: Optional[str] = None):
    candidates = [explicit] if explicit else []
    candidates.extend(("execute", "execute_action", "run", "coordinate"))
    for name in candidates:
        if not name:
            continue
        method = getattr(coordinator, name, None)
        if callable(method):
            return name, method
    raise AttributeError("S46 coordinator exposes no supported execution method")


class OutcomeAwareGovernedActionCoordinator:
    """Thin integration boundary: S46 execution -> S47 outcome intelligence."""

    def __init__(self, coordinator: Any, outcome_engine: Optional[ExecutionOutcomeIntelligence] = None,
                 execution_method: Optional[str] = None) -> None:
        self.coordinator = coordinator
        self.outcome_engine = outcome_engine or ExecutionOutcomeIntelligence()
        self.execution_method_name, self._execute = _resolve_execution_method(coordinator, execution_method)

    def execute_and_observe(
        self,
        *args: Any,
        project_id: str,
        action_id: str,
        expected: Any,
        actual: Any,
        evidence_refs: tuple[str, ...] = (),
        success_threshold: Optional[float] = None,
        observed_score: Optional[float] = None,
        notes: str = "",
        **kwargs: Any,
    ) -> OutcomeIntegratedExecutionResult:
        execution_result = self._execute(*args, **kwargs)
        receipt_id = _stable_receipt_id(project_id, action_id, execution_result)
        observation = OutcomeObservation(
            execution_receipt_id=receipt_id,
            project_id=project_id,
            action_id=action_id,
            expected=expected,
            actual=actual,
            evidence_refs=evidence_refs,
            success_threshold=success_threshold,
            observed_score=observed_score,
            notes=notes,
        )
        outcome = self.outcome_engine.record(observation)
        return OutcomeIntegratedExecutionResult(
            execution_result=execution_result,
            outcome=outcome,
            execution_receipt_id=receipt_id,
            external_action_executed=False,
            memory_write_executed=False,
        )
