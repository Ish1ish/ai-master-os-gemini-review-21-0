"""O45-S54 failure learning and adaptive recovery signal layer.

Consumes the bounded failure/recovery result produced by S53 and converts it
into a traceable learning signal plus an explicit next-decision route.
This layer does not write AI memory, execute actions, or change provider
credentials. It is intentionally deterministic and idempotent per recovery
run key.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Mapping
import hashlib
import json


@dataclass(frozen=True)
class FailureLearningSignal:
    signal_id: str
    recovery_run_id: str
    failure_class: str
    recovery_status: str
    statement: str
    evidence_refs: tuple[str, ...]
    retry_count: int
    next_decision: str
    scope: str = "execution_recovery"


@dataclass(frozen=True)
class AdaptiveRecoveryDecision:
    recovery_run_id: str
    decision: str
    rationale: str
    learning_signal_id: str
    evidence_refs: tuple[str, ...]
    execution_triggered: bool = False
    memory_write_executed: bool = False
    external_action_executed: bool = False


@dataclass(frozen=True)
class FailureLearningResult:
    status: str
    recovery_run_id: str
    failure_class: str
    learning_signal: FailureLearningSignal
    next_decision: str
    decision: AdaptiveRecoveryDecision
    idempotent_replay: bool


class FailureLearningRepository:
    """Small deterministic in-process trace repository; no AI-memory writes."""

    def __init__(self) -> None:
        self._records: dict[str, FailureLearningResult] = {}

    def put(self, key: str, result: FailureLearningResult) -> FailureLearningResult:
        existing = self._records.get(key)
        if existing is not None:
            return FailureLearningResult(
                status=existing.status,
                recovery_run_id=existing.recovery_run_id,
                failure_class=existing.failure_class,
                learning_signal=existing.learning_signal,
                next_decision=existing.next_decision,
                decision=existing.decision,
                idempotent_replay=True,
            )
        self._records[key] = result
        return result

    def snapshot(self) -> Mapping[str, FailureLearningResult]:
        return dict(self._records)


def _stable_id(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20].upper()


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class FailureLearningCoordinator:
    """Learn from S53 recovery outcomes and route the next decision explicitly."""

    def __init__(self, repository: FailureLearningRepository | None = None) -> None:
        self.repository = repository or FailureLearningRepository()

    def observe(self, recovery_result: Any, *, recovery_run_id: str) -> FailureLearningResult:
        injected_model = _coerce_int(getattr(recovery_result, "injected_model_failures", 0))
        injected_search = _coerce_int(getattr(recovery_result, "injected_search_failures", 0))
        model_attempts = _coerce_int(getattr(recovery_result, "model_attempts", 0))
        search_attempts = _coerce_int(getattr(recovery_result, "search_attempts", 0))

        if injected_model or injected_search:
            failure_class = "TRANSIENT_PROVIDER_FAILURE"
            recovery_status = "RECOVERED" if model_attempts > injected_model and search_attempts > injected_search else "PARTIAL_RECOVERY"
            next_decision = "BOUNDED_NEXT_STEP" if recovery_status == "RECOVERED" else "REASSESS_OR_CHANGE"
            statement = (
                "A bounded provider failure was injected and recovered; preserve the recovery boundary "
                "and continue only through a governed next decision."
            )
        else:
            failure_class = "NO_INJECTED_FAILURE"
            recovery_status = "SUCCESS"
            next_decision = "BOUNDED_NEXT_STEP"
            statement = "No failure signal was observed; retain the bounded recovery policy for future runs."

        evidence_refs = (
            f"recovery:{recovery_run_id}",
            f"model_attempts:{model_attempts}",
            f"search_attempts:{search_attempts}",
        )
        signal_id = "FLS-" + _stable_id({
            "run": recovery_run_id,
            "failure_class": failure_class,
            "recovery_status": recovery_status,
            "evidence_refs": evidence_refs,
        })
        signal = FailureLearningSignal(
            signal_id=signal_id,
            recovery_run_id=recovery_run_id,
            failure_class=failure_class,
            recovery_status=recovery_status,
            statement=statement,
            evidence_refs=evidence_refs,
            retry_count=max(model_attempts, search_attempts),
            next_decision=next_decision,
        )
        decision = AdaptiveRecoveryDecision(
            recovery_run_id=recovery_run_id,
            decision=next_decision,
            rationale=statement,
            learning_signal_id=signal_id,
            evidence_refs=evidence_refs,
        )
        result = FailureLearningResult(
            status="RECORDED",
            recovery_run_id=recovery_run_id,
            failure_class=failure_class,
            learning_signal=signal,
            next_decision=next_decision,
            decision=decision,
            idempotent_replay=False,
        )
        return self.repository.put(recovery_run_id, result)


def result_to_dict(result: FailureLearningResult) -> dict[str, Any]:
    return asdict(result)
