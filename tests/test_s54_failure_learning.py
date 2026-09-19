from __future__ import annotations

from dataclasses import dataclass

from core.src.real_provider_failure_learning import (
    FailureLearningCoordinator,
    FailureLearningRepository,
)


@dataclass
class FakeRecoveryResult:
    injected_model_failures: int = 1
    injected_search_failures: int = 1
    model_attempts: int = 3
    search_attempts: int = 3


def test_transient_failure_becomes_learning_signal():
    out = FailureLearningCoordinator().observe(FakeRecoveryResult(), recovery_run_id="R-001")
    assert out.status == "RECORDED"
    assert out.learning_signal.failure_class == "TRANSIENT_PROVIDER_FAILURE"
    assert out.learning_signal.recovery_status == "RECOVERED"


def test_learning_signal_is_traceable():
    out = FailureLearningCoordinator().observe(FakeRecoveryResult(), recovery_run_id="R-002")
    assert out.learning_signal.recovery_run_id == "R-002"
    assert all(ref for ref in out.learning_signal.evidence_refs)


def test_next_decision_is_explicit():
    out = FailureLearningCoordinator().observe(FakeRecoveryResult(), recovery_run_id="R-003")
    assert out.next_decision == "BOUNDED_NEXT_STEP"
    assert out.decision.decision == out.next_decision


def test_failure_learning_does_not_execute():
    out = FailureLearningCoordinator().observe(FakeRecoveryResult(), recovery_run_id="R-004")
    assert out.decision.execution_triggered is False
    assert out.decision.external_action_executed is False
    assert out.decision.memory_write_executed is False


def test_idempotent_replay():
    repo = FailureLearningRepository()
    coordinator = FailureLearningCoordinator(repo)
    first = coordinator.observe(FakeRecoveryResult(), recovery_run_id="R-005")
    second = coordinator.observe(FakeRecoveryResult(), recovery_run_id="R-005")
    assert first.learning_signal.signal_id == second.learning_signal.signal_id
    assert second.idempotent_replay is True


def test_no_failure_routes_to_bounded_next_step():
    out = FailureLearningCoordinator().observe(
        FakeRecoveryResult(0, 0, 1, 1), recovery_run_id="R-006"
    )
    assert out.failure_class == "NO_INJECTED_FAILURE"
    assert out.next_decision == "BOUNDED_NEXT_STEP"


def test_partial_recovery_routes_to_reassessment():
    out = FailureLearningCoordinator().observe(
        FakeRecoveryResult(1, 1, 3, 1), recovery_run_id="R-007"
    )
    assert out.learning_signal.recovery_status == "PARTIAL_RECOVERY"
    assert out.next_decision == "REASSESS_OR_CHANGE"


def test_retry_count_is_traceable():
    out = FailureLearningCoordinator().observe(
        FakeRecoveryResult(1, 1, 4, 3), recovery_run_id="R-008"
    )
    assert out.learning_signal.retry_count == 4


def test_same_repo_keeps_single_trace():
    repo = FailureLearningRepository()
    coordinator = FailureLearningCoordinator(repo)
    coordinator.observe(FakeRecoveryResult(), recovery_run_id="R-009")
    coordinator.observe(FakeRecoveryResult(), recovery_run_id="R-009")
    assert len(repo.snapshot()) == 1


def test_signal_id_is_deterministic_for_same_input():
    a = FailureLearningCoordinator().observe(FakeRecoveryResult(), recovery_run_id="R-010")
    b = FailureLearningCoordinator().observe(FakeRecoveryResult(), recovery_run_id="R-010")
    assert a.learning_signal.signal_id == b.learning_signal.signal_id


def test_scope_is_execution_recovery():
    out = FailureLearningCoordinator().observe(FakeRecoveryResult(), recovery_run_id="R-011")
    assert out.learning_signal.scope == "execution_recovery"


def test_decision_contains_signal_reference():
    out = FailureLearningCoordinator().observe(FakeRecoveryResult(), recovery_run_id="R-012")
    assert out.decision.learning_signal_id == out.learning_signal.signal_id


def run_all():
    tests = [v for n, v in globals().items() if n.startswith("test_")]
    for test in tests:
        test()
    print(f"S54_TARGETED_TESTS_PASS {len(tests)}/{len(tests)}")


if __name__ == "__main__":
    run_all()
