"""O45-S56 cost-aware adaptive recovery policy.

Takes the deterministic S55 recovery policy and applies a hard recovery budget
before any provider retry/fallback could be considered. This is a planning and
governance boundary only: it never executes a provider call, external action,
or AI-memory write.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Mapping
import hashlib
import json


@dataclass(frozen=True)
class RecoveryBudget:
    budget_id: str
    max_budget_units: int
    estimated_units: int
    remaining_units: int
    max_provider_calls: int
    estimated_provider_calls: int
    within_budget: bool
    budget_policy: str


@dataclass(frozen=True)
class CostAwareRecoveryResult:
    status: str
    recovery_run_id: str
    policy_id: str
    strategy: str
    original_max_attempts: int
    effective_max_attempts: int
    budget: RecoveryBudget
    next_decision: str
    rationale: str
    evidence_refs: tuple[str, ...]
    execution_triggered: bool = False
    external_action_executed: bool = False
    memory_write_executed: bool = False
    idempotent_replay: bool = False


class CostAwareRecoveryRepository:
    def __init__(self) -> None:
        self._records: dict[str, CostAwareRecoveryResult] = {}

    def put(self, key: str, result: CostAwareRecoveryResult) -> CostAwareRecoveryResult:
        existing = self._records.get(key)
        if existing is not None:
            return CostAwareRecoveryResult(
                status=existing.status,
                recovery_run_id=existing.recovery_run_id,
                policy_id=existing.policy_id,
                strategy=existing.strategy,
                original_max_attempts=existing.original_max_attempts,
                effective_max_attempts=existing.effective_max_attempts,
                budget=existing.budget,
                next_decision=existing.next_decision,
                rationale=existing.rationale,
                evidence_refs=existing.evidence_refs,
                execution_triggered=False,
                external_action_executed=False,
                memory_write_executed=False,
                idempotent_replay=True,
            )
        self._records[key] = result
        return result

    def snapshot(self) -> Mapping[str, CostAwareRecoveryResult]:
        return dict(self._records)


def _stable_id(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20].upper()


def _safe_int(value: Any, default: int, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, parsed)


def _estimate_units(*, attempts: int, model_unit_cost: int, search_unit_cost: int, backoff_steps: tuple[int, ...]) -> int:
    provider_calls = attempts * 2
    retry_wait_units = sum(backoff_steps)
    return attempts * (model_unit_cost + search_unit_cost) + retry_wait_units


def _policy_budget(max_attempts: int, backoff_steps: tuple[int, ...], *, max_budget_units: int, model_unit_cost: int, search_unit_cost: int) -> tuple[int, int, int, bool]:
    max_attempts = _safe_int(max_attempts, 1, 1)
    budget = _safe_int(max_budget_units, 1, 1)
    model_cost = _safe_int(model_unit_cost, 1, 1)
    search_cost = _safe_int(search_unit_cost, 1, 1)
    max_calls = max_attempts * 2
    estimated = _estimate_units(
        attempts=max_attempts,
        model_unit_cost=model_cost,
        search_unit_cost=search_cost,
        backoff_steps=backoff_steps,
    )
    if estimated <= budget:
        return max_attempts, max_calls, estimated, True

    per_attempt = max(1, model_cost + search_cost)
    effective = 0
    estimate = 0
    for attempt in range(1, max_attempts + 1):
        attempt_cost = attempt * per_attempt + sum(backoff_steps[: max(0, attempt - 1)])
        if attempt_cost <= budget:
            effective = attempt
            estimate = attempt_cost
        else:
            break
    return effective, effective * 2, estimate, effective > 0


class CostAwareRecoveryCoordinator:
    """Adds a hard cost/retry budget to the S55 policy without executing it."""

    def __init__(self, repository: CostAwareRecoveryRepository | None = None, *, max_budget_units: int = 10,
                 model_unit_cost: int = 2, search_unit_cost: int = 1) -> None:
        self.repository = repository or CostAwareRecoveryRepository()
        self.max_budget_units = _safe_int(max_budget_units, 10, 1)
        self.model_unit_cost = _safe_int(model_unit_cost, 2, 1)
        self.search_unit_cost = _safe_int(search_unit_cost, 1, 1)

    def apply(self, policy_result: Any, *, recovery_run_id: str | None = None) -> CostAwareRecoveryResult:
        run_id = recovery_run_id or policy_result.recovery_run_id
        policy = policy_result.policy
        effective, provider_calls, estimated, within = _policy_budget(
            policy.max_attempts,
            tuple(policy.backoff_steps),
            max_budget_units=self.max_budget_units,
            model_unit_cost=self.model_unit_cost,
            search_unit_cost=self.search_unit_cost,
        )
        budget_id = "BUD-" + _stable_id({
            "policy_id": policy.policy_id,
            "run": run_id,
            "max_budget_units": self.max_budget_units,
            "model_unit_cost": self.model_unit_cost,
            "search_unit_cost": self.search_unit_cost,
            "effective": effective,
        })
        if within:
            strategy = policy.strategy
            next_decision = policy_result.next_decision
            rationale = "S55 recovery policy is within the configured recovery budget."
            budget_policy = "ALLOW_BOUNDED_RECOVERY"
            status = "BUDGETED"
        else:
            strategy = "BUDGET_EXCEEDED_FAIL_CLOSED"
            next_decision = "COLLECT_MORE_EVIDENCE"
            rationale = "Configured recovery budget cannot safely fund one bounded recovery attempt; fail closed."
            budget_policy = "FAIL_CLOSED_BUDGET_EXCEEDED"
            status = "BUDGET_BLOCKED"

        remaining = max(0, self.max_budget_units - estimated)
        budget = RecoveryBudget(
            budget_id=budget_id,
            max_budget_units=self.max_budget_units,
            estimated_units=estimated,
            remaining_units=remaining,
            max_provider_calls=policy.max_attempts * 2,
            estimated_provider_calls=provider_calls,
            within_budget=within,
            budget_policy=budget_policy,
        )
        evidence_refs = tuple(policy_result.evidence_refs) + (
            f"policy:{policy.policy_id}",
            f"budget:{budget_id}",
        )
        result = CostAwareRecoveryResult(
            status=status,
            recovery_run_id=run_id,
            policy_id=policy.policy_id,
            strategy=strategy,
            original_max_attempts=policy.max_attempts,
            effective_max_attempts=effective,
            budget=budget,
            next_decision=next_decision,
            rationale=rationale,
            evidence_refs=evidence_refs,
        )
        return self.repository.put(run_id, result)


def result_to_dict(result: CostAwareRecoveryResult) -> dict[str, Any]:
    return asdict(result)
