"""O45-S55 deterministic adaptive recovery policy engine.

Consumes S54 failure-learning results and turns learning signals into an explicit,
bounded recovery policy. The policy is deterministic, idempotent, and never
executes actions, writes AI memory, or changes provider configuration.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Mapping
import hashlib
import json


@dataclass(frozen=True)
class RecoveryPolicy:
    policy_id: str
    failure_class: str
    recovery_status: str
    strategy: str
    max_attempts: int
    backoff_steps: tuple[int, ...]
    fallback: str
    terminal_route: str
    bounded: bool = True
    execution_allowed: bool = False
    external_action_allowed: bool = False
    memory_write_allowed: bool = False


@dataclass(frozen=True)
class AdaptiveRecoveryPolicyResult:
    status: str
    recovery_run_id: str
    learning_signal_id: str
    policy: RecoveryPolicy
    next_decision: str
    rationale: str
    evidence_refs: tuple[str, ...]
    idempotent_replay: bool = False


class AdaptiveRecoveryPolicyRepository:
    def __init__(self) -> None:
        self._records: dict[str, AdaptiveRecoveryPolicyResult] = {}

    def put(self, key: str, result: AdaptiveRecoveryPolicyResult) -> AdaptiveRecoveryPolicyResult:
        existing = self._records.get(key)
        if existing is not None:
            return AdaptiveRecoveryPolicyResult(
                status=existing.status,
                recovery_run_id=existing.recovery_run_id,
                learning_signal_id=existing.learning_signal_id,
                policy=existing.policy,
                next_decision=existing.next_decision,
                rationale=existing.rationale,
                evidence_refs=existing.evidence_refs,
                idempotent_replay=True,
            )
        self._records[key] = result
        return result

    def snapshot(self) -> Mapping[str, AdaptiveRecoveryPolicyResult]:
        return dict(self._records)


def _stable_id(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20].upper()


def _policy_for(failure_class: str, recovery_status: str) -> tuple[str, int, tuple[int, ...], str, str, str]:
    # Deterministic policy table. No policy authorizes execution.
    if recovery_status == "RECOVERED":
        return ("RETRY_THEN_CONTINUE", 3, (1, 2), "PROVIDER_RETRY", "BOUNDED_NEXT_STEP", "Recovered within bounded retry envelope.")
    if recovery_status == "PARTIAL_RECOVERY":
        return ("RETRY_THEN_REASSESS", 2, (1,), "FALLBACK_AND_REASSESS", "REASSESS_OR_CHANGE", "Recovery was partial; reduce retry budget and reassess.")
    if failure_class in {"TRANSIENT_PROVIDER_FAILURE", "NO_INJECTED_FAILURE"}:
        return ("BOUNDED_RETRY", 3, (1, 2), "CONTROLLED_STOP", "BOUNDED_NEXT_STEP", "Use bounded retry and preserve governance boundaries.")
    return ("FAIL_CLOSED", 1, tuple(), "CONTROLLED_STOP", "COLLECT_MORE_EVIDENCE", "Unknown failure class routes to fail-closed evidence collection.")


class AdaptiveRecoveryPolicyCoordinator:
    def __init__(self, repository: AdaptiveRecoveryPolicyRepository | None = None) -> None:
        self.repository = repository or AdaptiveRecoveryPolicyRepository()

    def select(self, learning_result: Any, *, recovery_run_id: str | None = None) -> AdaptiveRecoveryPolicyResult:
        signal = learning_result.learning_signal
        run_id = recovery_run_id or learning_result.recovery_run_id
        strategy, max_attempts, backoff_steps, fallback, next_decision, rationale = _policy_for(
            signal.failure_class, signal.recovery_status
        )
        policy_id = "ARP-" + _stable_id({
            "failure_class": signal.failure_class,
            "recovery_status": signal.recovery_status,
            "strategy": strategy,
            "max_attempts": max_attempts,
            "backoff_steps": backoff_steps,
            "fallback": fallback,
        })
        policy = RecoveryPolicy(
            policy_id=policy_id,
            failure_class=signal.failure_class,
            recovery_status=signal.recovery_status,
            strategy=strategy,
            max_attempts=max_attempts,
            backoff_steps=backoff_steps,
            fallback=fallback,
            terminal_route=next_decision,
        )
        evidence_refs = tuple(signal.evidence_refs) + (f"learning:{signal.signal_id}",)
        result = AdaptiveRecoveryPolicyResult(
            status="POLICY_SELECTED",
            recovery_run_id=run_id,
            learning_signal_id=signal.signal_id,
            policy=policy,
            next_decision=next_decision,
            rationale=rationale,
            evidence_refs=evidence_refs,
        )
        return self.repository.put(run_id, result)


def result_to_dict(result: AdaptiveRecoveryPolicyResult) -> dict[str, Any]:
    return asdict(result)
