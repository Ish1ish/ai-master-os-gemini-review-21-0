from __future__ import annotations

from core.src.execution_outcome_persistence import (
    InMemoryOutcomeDecisionRepository,
    OutcomePersistedGovernedActionCoordinator,
)


class FakeS46Coordinator:
    def __init__(self):
        self.calls = 0

    def execute(self, payload):
        self.calls += 1
        return {
            "status": "COMPLETE",
            "execution_receipt_id": "R-S46-S49-001",
            "payload": payload,
            "external_action_executed": False,
        }


def test_success_persists_and_routes_next_decision():
    repo = InMemoryOutcomeDecisionRepository()
    c = OutcomePersistedGovernedActionCoordinator(FakeS46Coordinator(), repo)
    result = c.execute_and_record({"intent": "test"}, project_id="P1", action_id="A1", expected="COMPLETE", actual="COMPLETE", evidence_refs=("E1",))
    assert result.trace.outcome_status == "SUCCESS"
    assert result.next_decision == "BOUNDED_NEXT_STEP"
    assert result.memory_write_executed is False


def test_failure_persists_reassessment():
    repo = InMemoryOutcomeDecisionRepository()
    c = OutcomePersistedGovernedActionCoordinator(FakeS46Coordinator(), repo)
    result = c.execute_and_record({"intent": "test"}, project_id="P1", action_id="A2", expected="COMPLETE", actual="FAILED")
    assert result.trace.outcome_status == "FAILURE"
    assert result.next_decision == "REASSESS_OR_CHANGE"


def test_inconclusive_persists_without_learning_signal():
    repo = InMemoryOutcomeDecisionRepository()
    c = OutcomePersistedGovernedActionCoordinator(FakeS46Coordinator(), repo)
    result = c.execute_and_record({"intent": "test"}, project_id="P1", action_id="A3", expected="COMPLETE", actual=None)
    assert result.trace.outcome_status == "INCONCLUSIVE"
    assert result.trace.learning_signal_id is None
    assert result.next_decision == "COLLECT_MORE_EVIDENCE"


def test_same_receipt_is_idempotent_in_repository():
    repo = InMemoryOutcomeDecisionRepository()
    c = OutcomePersistedGovernedActionCoordinator(FakeS46Coordinator(), repo)
    first = c.execute_and_record({"intent": "test"}, project_id="P1", action_id="A4", expected="COMPLETE", actual="COMPLETE")
    second = c.execute_and_record({"intent": "test"}, project_id="P1", action_id="A4", expected="COMPLETE", actual="FAILED")
    assert first.trace == second.trace
    assert len(repo.snapshot()) == 1


def test_trace_can_be_retrieved_by_receipt():
    repo = InMemoryOutcomeDecisionRepository()
    c = OutcomePersistedGovernedActionCoordinator(FakeS46Coordinator(), repo)
    result = c.execute_and_record({"intent": "test"}, project_id="P1", action_id="A5", expected="COMPLETE", actual="COMPLETE")
    assert c.get_trace(result.execution.execution_receipt_id) == result.trace


def test_learning_signal_id_is_traceable_when_present():
    repo = InMemoryOutcomeDecisionRepository()
    c = OutcomePersistedGovernedActionCoordinator(FakeS46Coordinator(), repo)
    result = c.execute_and_record({"intent": "test"}, project_id="P1", action_id="A6", expected="COMPLETE", actual="COMPLETE", evidence_refs=("E-A", "E-B"))
    assert result.trace.learning_signal_id == result.execution.outcome.learning_signal.signal_id
    assert result.trace.evidence_refs == ("E-A", "E-B")


def test_external_execution_remains_blocked():
    repo = InMemoryOutcomeDecisionRepository()
    result = OutcomePersistedGovernedActionCoordinator(FakeS46Coordinator(), repo).execute_and_record(
        {"intent": "test"}, project_id="P1", action_id="A7", expected="COMPLETE", actual="COMPLETE"
    )
    assert result.external_action_executed is False


def test_memory_write_remains_blocked():
    repo = InMemoryOutcomeDecisionRepository()
    result = OutcomePersistedGovernedActionCoordinator(FakeS46Coordinator(), repo).execute_and_record(
        {"intent": "test"}, project_id="P1", action_id="A8", expected="COMPLETE", actual="COMPLETE"
    )
    assert result.memory_write_executed is False
    assert result.trace.memory_write_executed is False


def test_trace_has_stable_version_and_id():
    repo = InMemoryOutcomeDecisionRepository()
    result = OutcomePersistedGovernedActionCoordinator(FakeS46Coordinator(), repo).execute_and_record(
        {"intent": "test"}, project_id="P1", action_id="A9", expected="COMPLETE", actual="COMPLETE"
    )
    assert result.trace.trace_version == "O45-S49-v1"
    assert result.trace_id.startswith("TRACE-")


def test_existing_s48_execution_is_not_reimplemented():
    coordinator = FakeS46Coordinator()
    wrapper = OutcomePersistedGovernedActionCoordinator(coordinator, InMemoryOutcomeDecisionRepository())
    result = wrapper.execute_and_record({"intent": "delegated"}, project_id="P1", action_id="A10", expected="COMPLETE", actual="COMPLETE")
    assert coordinator.calls == 1
    assert result.execution.execution_result["payload"] == {"intent": "delegated"}


def run_all():
    tests = [v for n, v in globals().items() if n.startswith("test_")]
    for test in tests:
        test()
    print(f"S49_TARGETED_TESTS_PASS {len(tests)}/{len(tests)}")


if __name__ == "__main__":
    run_all()
