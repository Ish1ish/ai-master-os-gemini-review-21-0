from __future__ import annotations
from dataclasses import dataclass
from core.src.real_provider_failure_learning import FailureLearningCoordinator
from core.src.adaptive_recovery_policy import AdaptiveRecoveryPolicyCoordinator, AdaptiveRecoveryPolicyRepository

@dataclass
class Recovery:
    injected_model_failures: int = 1
    injected_search_failures: int = 1
    model_attempts: int = 3
    search_attempts: int = 3

def learned(run_id="S55-RUN-001", **kw):
    return FailureLearningCoordinator().observe(Recovery(**kw), recovery_run_id=run_id)

def test_recovered_policy_is_bounded():
    r = AdaptiveRecoveryPolicyCoordinator().select(learned())
    assert r.policy.strategy == "RETRY_THEN_CONTINUE"
    assert r.policy.max_attempts == 3 and r.policy.bounded

def test_partial_recovery_reassesses():
    r = AdaptiveRecoveryPolicyCoordinator().select(learned("R2", model_attempts=3, search_attempts=1))
    assert r.policy.strategy == "RETRY_THEN_REASSESS"
    assert r.next_decision == "REASSESS_OR_CHANGE"

def test_unknown_class_fail_closed():
    class L: pass
    class S: pass
    s=S(); s.failure_class="UNKNOWN"; s.recovery_status="BROKEN"; s.evidence_refs=("x",); s.signal_id="SIG"; 
    l=L(); l.learning_signal=s; l.recovery_run_id="R3"
    r=AdaptiveRecoveryPolicyCoordinator().select(l)
    assert r.policy.strategy == "FAIL_CLOSED"
    assert r.next_decision == "COLLECT_MORE_EVIDENCE"

def test_policy_never_executes():
    r=AdaptiveRecoveryPolicyCoordinator().select(learned("R4"))
    assert r.policy.execution_allowed is False
    assert r.policy.external_action_allowed is False
    assert r.policy.memory_write_allowed is False

def test_evidence_carries_learning_signal():
    r=AdaptiveRecoveryPolicyCoordinator().select(learned("R5"))
    assert "learning:" + r.learning_signal_id in r.evidence_refs

def test_policy_id_is_deterministic():
    a=AdaptiveRecoveryPolicyCoordinator().select(learned("R6"))
    b=AdaptiveRecoveryPolicyCoordinator().select(learned("R6"))
    assert a.policy.policy_id == b.policy.policy_id

def test_idempotent_repository():
    repo=AdaptiveRecoveryPolicyRepository(); c=AdaptiveRecoveryPolicyCoordinator(repo)
    a=c.select(learned("R7")); b=c.select(learned("R7"))
    assert b.idempotent_replay is True and len(repo.snapshot())==1

def test_backoff_is_bounded():
    r=AdaptiveRecoveryPolicyCoordinator().select(learned("R8"))
    assert max(r.policy.backoff_steps) <= 2

def test_fallback_is_explicit():
    r=AdaptiveRecoveryPolicyCoordinator().select(learned("R9", model_attempts=3, search_attempts=1))
    assert r.policy.fallback == "FALLBACK_AND_REASSESS"

def test_terminal_route_is_explicit():
    r=AdaptiveRecoveryPolicyCoordinator().select(learned("R10"))
    assert r.policy.terminal_route == "BOUNDED_NEXT_STEP"

def test_scope_indirectly_preserved():
    r=AdaptiveRecoveryPolicyCoordinator().select(learned("R11"))
    assert any(ref.startswith("recovery:") for ref in r.evidence_refs)

def test_policy_traceable_to_run():
    r=AdaptiveRecoveryPolicyCoordinator().select(learned("R12"))
    assert r.recovery_run_id == "R12"

def test_no_failure_stays_bounded():
    r=AdaptiveRecoveryPolicyCoordinator().select(learned("R13", injected_model_failures=0, injected_search_failures=0, model_attempts=1, search_attempts=1))
    assert r.policy.strategy in {"BOUNDED_RETRY", "RETRY_THEN_CONTINUE"}
    assert r.policy.bounded

def test_result_status():
    r=AdaptiveRecoveryPolicyCoordinator().select(learned("R14"))
    assert r.status == "POLICY_SELECTED"

def run_all():
    tests=[v for n,v in globals().items() if n.startswith('test_')]
    for t in tests: t()
    print(f"S55_TARGETED_TESTS_PASS {len(tests)}/{len(tests)}")

if __name__=='__main__': run_all()
