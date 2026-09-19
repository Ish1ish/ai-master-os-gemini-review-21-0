from __future__ import annotations

from core.src.execution_outcome_intelligence import (
    ExecutionOutcomeIntelligence,
    OutcomeObservation,
    OutcomeStatus,
    classify_outcome,
)


def obs(receipt, expected, actual, **kwargs):
    return OutcomeObservation(
        execution_receipt_id=receipt,
        project_id="P1",
        action_id="A1",
        expected=expected,
        actual=actual,
        evidence_refs=("E1",),
        **kwargs,
    )


def test_success_creates_feedback_and_learning():
    out = ExecutionOutcomeIntelligence().record(obs("R1", "ok", "ok"))
    assert out.status == OutcomeStatus.SUCCESS.value
    assert out.decision_feedback == "SUPPORTS_DECISION"
    assert out.learning_signal is not None
    assert out.next_decision == "BOUNDED_NEXT_STEP"


def test_failure_creates_negative_feedback():
    out = ExecutionOutcomeIntelligence().record(obs("R2", "ok", "bad"))
    assert out.status == OutcomeStatus.FAILURE.value
    assert out.decision_feedback == "CONTRADICTS_DECISION"
    assert out.learning_signal is not None
    assert out.next_decision == "REASSESS_OR_CHANGE"


def test_inconclusive_does_not_create_learning_signal():
    out = ExecutionOutcomeIntelligence().record(obs("R3", "ok", None))
    assert out.status == OutcomeStatus.INCONCLUSIVE.value
    assert out.decision_feedback == "INSUFFICIENT_EVIDENCE"
    assert out.learning_signal is None
    assert out.next_decision == "COLLECT_MORE_EVIDENCE"


def test_threshold_success_is_deterministic():
    status, matched = classify_outcome(obs("R4", None, None, success_threshold=0.8, observed_score=0.9))
    assert status == OutcomeStatus.SUCCESS and matched is True


def test_threshold_failure_is_deterministic():
    status, matched = classify_outcome(obs("R5", None, None, success_threshold=0.8, observed_score=0.4))
    assert status == OutcomeStatus.FAILURE and matched is False


def test_idempotent_receipt_replay():
    engine = ExecutionOutcomeIntelligence()
    first = engine.record(obs("R6", "ok", "ok"))
    second = engine.record(obs("R6", "ok", "bad"))
    assert first == second
    assert len(engine.snapshot()) == 1


def test_provenance_preserved():
    out = ExecutionOutcomeIntelligence().record(obs("R7", "ok", "ok"))
    assert out.provenance["project_id"] == "P1"
    assert out.provenance["action_id"] == "A1"
    assert out.provenance["evidence_refs"] == ["E1"]


def test_memory_write_stays_blocked():
    out = ExecutionOutcomeIntelligence().record(obs("R8", "ok", "ok"))
    assert out.memory_write_executed is False


def run_all():
    tests = [v for n, v in globals().items() if n.startswith("test_")]
    for test in tests:
        test()
    print(f"S47_TARGETED_TESTS_PASS {len(tests)}/{len(tests)}")


if __name__ == "__main__":
    run_all()
