from __future__ import annotations

from core.src.execution_outcome_persistence import InMemoryOutcomeDecisionRepository, OutcomePersistedGovernedActionCoordinator
from core.src.decision_loop_reentry import (
    DecisionLoopReentryCoordinator,
    InMemoryDecisionLoopReentryRepository,
)


class FakeS46Coordinator:
    def execute(self, payload):
        return {
            "status": "COMPLETE",
            "execution_receipt_id": "R-S50-001",
            "payload": payload,
            "external_action_executed": False,
        }


def make_trace():
    repo = InMemoryOutcomeDecisionRepository()
    c = OutcomePersistedGovernedActionCoordinator(FakeS46Coordinator(), repo)
    result = c.execute_and_record(
        {"intent": "reentry"},
        project_id="P-S50",
        action_id="A-S50",
        expected="COMPLETE",
        actual="COMPLETE",
        evidence_refs=("E-S50-1", "E-S50-2"),
    )
    return repo, result


def test_reentry_context_comes_from_s49_trace():
    repo, result = make_trace()
    loop_repo = InMemoryDecisionLoopReentryRepository()
    out = DecisionLoopReentryCoordinator(repo, loop_repo).reenter_from_receipt(result.execution.execution_receipt_id)
    assert out is not None
    assert out.context.source_trace_id == result.trace.trace_id
    assert out.context.next_decision == "BOUNDED_NEXT_STEP"


def test_next_decision_is_preserved():
    repo, result = make_trace()
    out = DecisionLoopReentryCoordinator(repo).reenter_from_receipt(result.execution.execution_receipt_id)
    assert out.context.next_decision == result.next_decision


def test_evidence_refs_are_carried_forward():
    repo, result = make_trace()
    out = DecisionLoopReentryCoordinator(repo).reenter_from_receipt(result.execution.execution_receipt_id)
    assert out.context.evidence_refs == ("E-S50-1", "E-S50-2")


def test_missing_receipt_does_not_create_loop():
    repo = InMemoryOutcomeDecisionRepository()
    loop_repo = InMemoryDecisionLoopReentryRepository()
    out = DecisionLoopReentryCoordinator(repo, loop_repo).reenter_from_receipt("missing")
    assert out is None
    assert len(loop_repo.snapshot()) == 0


def test_reentry_is_idempotent():
    repo, result = make_trace()
    loop_repo = InMemoryDecisionLoopReentryRepository()
    c = DecisionLoopReentryCoordinator(repo, loop_repo)
    first = c.reenter_from_receipt(result.execution.execution_receipt_id)
    second = c.reenter_from_receipt(result.execution.execution_receipt_id)
    assert first.context == second.context
    assert len(loop_repo.snapshot()) == 1


def test_reentry_does_not_execute_action():
    repo, result = make_trace()
    out = DecisionLoopReentryCoordinator(repo).reenter_from_receipt(result.execution.execution_receipt_id)
    assert out.execution_triggered is False
    assert out.external_action_executed is False


def test_reentry_does_not_write_memory():
    repo, result = make_trace()
    out = DecisionLoopReentryCoordinator(repo).reenter_from_receipt(result.execution.execution_receipt_id)
    assert out.memory_write_executed is False
    assert out.context.memory_write_executed is False


def test_loop_id_is_stable():
    repo, result = make_trace()
    c = DecisionLoopReentryCoordinator(repo)
    first = c.reenter_from_receipt(result.execution.execution_receipt_id)
    second = c.reenter_from_receipt(result.execution.execution_receipt_id)
    assert first.context.loop_id == second.context.loop_id
    assert first.context.loop_id.startswith("LOOP-")


def test_decision_feedback_is_preserved():
    repo, result = make_trace()
    out = DecisionLoopReentryCoordinator(repo).reenter_from_receipt(result.execution.execution_receipt_id)
    assert out.context.decision_feedback == result.trace.decision_feedback


def test_versioned_source_trace_is_visible():
    repo, result = make_trace()
    out = DecisionLoopReentryCoordinator(repo).reenter_from_receipt(result.execution.execution_receipt_id)
    assert out.context.reentry_version == "O45-S50-v1"
    assert out.context.source_trace_version == "O45-S49-v1"


def run_all():
    tests = [v for n, v in globals().items() if n.startswith("test_")]
    for test in tests:
        test()
    print(f"S50_TARGETED_TESTS_PASS {len(tests)}/{len(tests)}")


if __name__ == "__main__":
    run_all()
