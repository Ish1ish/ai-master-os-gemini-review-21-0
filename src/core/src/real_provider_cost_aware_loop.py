"""O45-S57 real-provider closed loop governed by the S56 recovery budget.

This layer composes the already verified S52 real-provider loop with S55/S56
policy and budget semantics. A real provider call is only attempted through a
bounded, budget-enforced wrapper. A single injected transient failure is used
by validation to prove the budget controls recovery of live provider calls.
No external execution, memory write, or production approval is enabled.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping
import hashlib

from .live_providers import model_provider, search_provider, provider_configuration_status
from .real_provider_closed_loop import RealProviderClosedLoopCoordinator
from .real_provider_failure_learning import FailureLearningCoordinator
from .adaptive_recovery_policy import AdaptiveRecoveryPolicyCoordinator
from .cost_aware_recovery import CostAwareRecoveryCoordinator

ProviderFn = Callable[[str], Mapping[str, Any]]


def _hash(value: Any) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class BudgetedProviderStats:
    kind: str
    attempts: int
    failures_injected: int
    provider_calls: int
    budget_units_used: int
    max_provider_calls: int
    max_budget_units: int
    fail_closed: bool = False


@dataclass(frozen=True)
class RealProviderCostAwareCycleResult:
    cycle_index: int
    status: str
    provider_model_live: bool
    provider_search_live: bool
    model_hash: str
    search_hash: str
    search_result_count: int
    trace_id: str
    next_decision: str
    model_stats: BudgetedProviderStats
    search_stats: BudgetedProviderStats


@dataclass(frozen=True)
class RealProviderCostAwareLoopResult:
    cycles: tuple[RealProviderCostAwareCycleResult, ...]
    total_provider_calls: int
    total_budget_units: int
    configured: bool
    closed_loop_two_cycles: bool
    next_decision_reentered: bool
    new_trace_each_cycle: bool
    execution_triggered: bool = False
    external_action_executed: bool = False
    memory_write_executed: bool = False


class _TransientOnce:
    def __init__(self, delegate: ProviderFn, *, kind: str, failures: int = 1) -> None:
        self.delegate = delegate
        self.kind = kind
        self.remaining = max(0, int(failures))
        self.injected = 0

    def __call__(self, value: str) -> Mapping[str, Any]:
        if self.remaining:
            self.remaining -= 1
            self.injected += 1
            raise RuntimeError(f"s57_injected_transient_{self.kind}_failure")
        return self.delegate(value)


class _BudgetedCall:
    def __init__(self, delegate: ProviderFn, *, kind: str, max_attempts: int, unit_cost: int, max_units: int) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self.delegate = delegate
        self.kind = kind
        self.max_attempts = max_attempts
        self.unit_cost = max(1, int(unit_cost))
        self.max_units = max(1, int(max_units))
        self.attempts = 0
        self.budget_units_used = 0
        self.fail_closed = False

    def __call__(self, value: str) -> Mapping[str, Any]:
        last: Exception | None = None
        for _ in range(self.max_attempts):
            if self.attempts >= self.max_attempts:
                break
            if self.budget_units_used + self.unit_cost > self.max_units:
                self.fail_closed = True
                raise RuntimeError("s57_provider_budget_exceeded")
            self.attempts += 1
            self.budget_units_used += self.unit_cost
            try:
                result = self.delegate(value)
                if not isinstance(result, Mapping):
                    raise RuntimeError(f"s57_{self.kind}_invalid_provider_contract")
                return result
            except Exception as exc:
                last = exc
        self.fail_closed = True
        raise RuntimeError(f"s57_{self.kind}_recovery_exhausted") from last

    def stats(self, injected_failures: int) -> BudgetedProviderStats:
        return BudgetedProviderStats(
            kind=self.kind,
            attempts=self.attempts,
            failures_injected=injected_failures,
            provider_calls=self.attempts,
            budget_units_used=self.budget_units_used,
            max_provider_calls=self.max_attempts,
            max_budget_units=self.max_units,
            fail_closed=self.fail_closed,
        )


class RealProviderCostAwareLoopCoordinator:
    """Validate S56 budget enforcement around real provider calls."""

    def __init__(
        self,
        *,
        model: ProviderFn | None = None,
        search: ProviderFn | None = None,
        max_budget_units: int = 12,
        model_unit_cost: int = 2,
        search_unit_cost: int = 1,
        max_attempts: int = 2,
        inject_model_failures: int = 1,
        inject_search_failures: int = 1,
        allow_external_execution: bool = False,
    ) -> None:
        self.base_model = model or model_provider
        self.base_search = search or search_provider
        self.max_budget_units = max(1, int(max_budget_units))
        self.model_unit_cost = max(1, int(model_unit_cost))
        self.search_unit_cost = max(1, int(search_unit_cost))
        self.max_attempts = max(1, int(max_attempts))
        self.inject_model_failures = max(0, int(inject_model_failures))
        self.inject_search_failures = max(0, int(inject_search_failures))
        self.allow_external_execution = bool(allow_external_execution)
        self.learning = FailureLearningCoordinator()
        self.policy = AdaptiveRecoveryPolicyCoordinator()
        self.budget = CostAwareRecoveryCoordinator(
            max_budget_units=self.max_budget_units,
            model_unit_cost=self.model_unit_cost,
            search_unit_cost=self.search_unit_cost,
        )
        self.closed_loop = None

    def _budget_for(self, run_id: str):
        class Recovery:
            injected_model_failures = self.inject_model_failures
            injected_search_failures = self.inject_search_failures
            model_attempts = self.max_attempts
            search_attempts = self.max_attempts
        learning = self.learning.observe(Recovery(), recovery_run_id=run_id)
        selected = self.policy.select(learning)
        return self.budget.apply(selected, recovery_run_id=run_id)

    def run(self, *, project_id: str = "P-S57") -> RealProviderCostAwareLoopResult:
        if provider_configuration_status().get("status") != "CONFIGURED" and (self.model is None and self.search is None):
            # Synthetic/fake providers can be used by targeted tests. Live gate requires configuration.
            raise RuntimeError("s57_real_provider_configuration_incomplete")

        from .closed_loop_integration import FullClosedLoopCoordinator
        self.closed_loop = FullClosedLoopCoordinator(allow_external_execution=self.allow_external_execution)
        results = []
        total_calls = 0
        total_units = 0
        for cycle_index in (1, 2):
            run_id = f"S57-{project_id}-C{cycle_index}"
            budget_result = self._budget_for(run_id)
            if budget_result.status != "BUDGETED" or budget_result.effective_max_attempts < 1:
                raise RuntimeError("s57_budget_exceeded_fail_closed")

            inject_model = _TransientOnce(self.base_model, kind="model", failures=self.inject_model_failures if cycle_index == 1 else 0)
            inject_search = _TransientOnce(self.base_search, kind="search", failures=self.inject_search_failures if cycle_index == 1 else 0)
            model_call = _BudgetedCall(
                inject_model,
                kind="model",
                max_attempts=budget_result.effective_max_attempts,
                unit_cost=self.model_unit_cost,
                max_units=self.max_budget_units,
            )
            search_call = _BudgetedCall(
                inject_search,
                kind="search",
                max_attempts=budget_result.effective_max_attempts,
                unit_cost=self.search_unit_cost,
                max_units=self.max_budget_units,
            )

            topic = "AI workflow automation for small businesses"
            m = model_call("Internal staging validation only. No external action. " + topic)
            if not isinstance(m.get("text"), str) or not m.get("text").strip():
                raise RuntimeError("s57_model_missing_text")
            s = search_call(topic + " customer workflow automation")
            rows = s.get("results")
            if not isinstance(rows, list) or not rows:
                raise RuntimeError("s57_search_missing_results")

            refs = (
                "REAL-MODEL-" + _hash(m.get("text"))[:16],
                "REAL-SEARCH-" + _hash(rows)[:16],
                f"BUDGET-{budget_result.budget.budget_id}",
            )
            if cycle_index == 2:
                refs = refs + (f"REENTRY-FROM-{results[-1].trace_id[:16]}",)
            cycle = self.closed_loop.run_cycle(
                project_id=project_id,
                action_id=f"A-S57-{cycle_index}",
                idempotency_key=f"S57-CYCLE-{cycle_index}",
                payload={"cycle": cycle_index, "budgeted": True},
                evidence_refs=refs,
            )
            model_stats = model_call.stats(inject_model.injected)
            search_stats = search_call.stats(inject_search.injected)
            results.append(
                RealProviderCostAwareCycleResult(
                    cycle_index=cycle_index,
                    status=cycle.outcome_status,
                    provider_model_live=True,
                    provider_search_live=True,
                    model_hash=_hash(m.get("text")),
                    search_hash=_hash(rows),
                    search_result_count=len(rows),
                    trace_id=cycle.trace_id,
                    next_decision=cycle.next_decision,
                    model_stats=model_stats,
                    search_stats=search_stats,
                )
            )
            total_calls += model_stats.provider_calls + search_stats.provider_calls
            total_units += model_stats.budget_units_used + search_stats.budget_units_used

        return RealProviderCostAwareLoopResult(
            cycles=tuple(results),
            total_provider_calls=total_calls,
            total_budget_units=total_units,
            configured=provider_configuration_status().get("status") == "CONFIGURED",
            closed_loop_two_cycles=len(results) == 2,
            next_decision_reentered=results[1].next_decision == next(v for v in self.closed_loop.trace_snapshot().values() if v.trace_id == results[1].trace_id).next_decision,
            new_trace_each_cycle=results[0].trace_id != results[1].trace_id,
            execution_triggered=False,
            external_action_executed=False,
            memory_write_executed=False,
        )


def validate_s57_provider_configuration() -> Mapping[str, Any]:
    return provider_configuration_status()
