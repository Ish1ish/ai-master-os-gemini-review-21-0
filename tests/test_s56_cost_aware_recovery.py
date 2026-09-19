from __future__ import annotations
from dataclasses import dataclass
from core.src.real_provider_failure_learning import FailureLearningCoordinator
from core.src.adaptive_recovery_policy import AdaptiveRecoveryPolicyCoordinator
from core.src.cost_aware_recovery import CostAwareRecoveryCoordinator, CostAwareRecoveryRepository

@dataclass
class Recovery:
    injected_model_failures: int = 1
    injected_search_failures: int = 1
    model_attempts: int = 3
    search_attempts: int = 3

def policy(run_id="S56-RUN-001"):
    learning = FailureLearningCoordinator().observe(Recovery(), recovery_run_id=run_id)
    return AdaptiveRecoveryPolicyCoordinator().select(learning)

def test_within_budget_allows_bounded_policy():
    r = CostAwareRecoveryCoordinator(max_budget_units=20).apply(policy())
    assert r.status == "BUDGETED" and r.budget.within_budget
    assert r.effective_max_attempts == 3

def test_tight_budget_reduces_attempts():
    r = CostAwareRecoveryCoordinator(max_budget_units=7).apply(policy("R2"))
    assert r.status == "BUDGETED"
    assert 1 <= r.effective_max_attempts < r.original_max_attempts

def test_tiny_budget_fails_closed():
    r = CostAwareRecoveryCoordinator(max_budget_units=1).apply(policy("R3"))
    assert r.status == "BUDGET_BLOCKED"
    assert r.strategy == "BUDGET_EXCEEDED_FAIL_CLOSED"
    assert r.next_decision == "COLLECT_MORE_EVIDENCE"

def test_budget_is_hard_ceiling():
    r = CostAwareRecoveryCoordinator(max_budget_units=7).apply(policy("R4"))
    assert r.budget.estimated_units <= 7

def test_provider_calls_are_bounded():
    r = CostAwareRecoveryCoordinator(max_budget_units=20).apply(policy("R5"))
    assert r.budget.estimated_provider_calls <= r.budget.max_provider_calls

def test_evidence_is_traceable():
    r = CostAwareRecoveryCoordinator(max_budget_units=20).apply(policy("R6"))
    assert any(x.startswith("budget:") for x in r.evidence_refs)
    assert any(x.startswith("policy:") for x in r.evidence_refs)

def test_policy_id_survives():
    r = CostAwareRecoveryCoordinator(max_budget_units=20).apply(policy("R7"))
    assert r.policy_id

def test_next_decision_preserved_when_budgeted():
    r = CostAwareRecoveryCoordinator(max_budget_units=20).apply(policy("R8"))
    assert r.next_decision == "BOUNDED_NEXT_STEP"

def test_no_execution():
    r = CostAwareRecoveryCoordinator(max_budget_units=20).apply(policy("R9"))
    assert r.execution_triggered is False and r.external_action_executed is False

def test_no_memory_write():
    r = CostAwareRecoveryCoordinator(max_budget_units=20).apply(policy("R10"))
    assert r.memory_write_executed is False

def test_idempotent_repository():
    repo = CostAwareRecoveryRepository()
    c = CostAwareRecoveryCoordinator(repo, max_budget_units=20)
    a = c.apply(policy("R11")); b = c.apply(policy("R11"))
    assert b.idempotent_replay is True and len(repo.snapshot()) == 1

def test_deterministic_budget_id():
    a = CostAwareRecoveryCoordinator(max_budget_units=20).apply(policy("R12"))
    b = CostAwareRecoveryCoordinator(max_budget_units=20).apply(policy("R12"))
    assert a.budget.budget_id == b.budget.budget_id

def test_remaining_units_nonnegative():
    r = CostAwareRecoveryCoordinator(max_budget_units=7).apply(policy("R13"))
    assert r.budget.remaining_units >= 0

def test_budget_policy_explicit():
    a = CostAwareRecoveryCoordinator(max_budget_units=20).apply(policy("R14"))
    b = CostAwareRecoveryCoordinator(max_budget_units=1).apply(policy("R15"))
    assert a.budget.budget_policy == "ALLOW_BOUNDED_RECOVERY"
    assert b.budget.budget_policy == "FAIL_CLOSED_BUDGET_EXCEEDED"

def test_compile_safe_shape():
    r = CostAwareRecoveryCoordinator(max_budget_units=20).apply(policy("R16"))
    assert r.status in {"BUDGETED", "BUDGET_BLOCKED"}

def run_all():
    tests=[v for n,v in globals().items() if n.startswith('test_')]
    for t in tests: t()
    print(f"S56_TARGETED_TESTS_PASS {len(tests)}/{len(tests)}")

if __name__ == '__main__': run_all()
