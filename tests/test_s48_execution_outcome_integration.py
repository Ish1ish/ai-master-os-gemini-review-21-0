from __future__ import annotations

from core.src.execution_outcome_integration import OutcomeAwareGovernedActionCoordinator
from core.src.execution_outcome_intelligence import ExecutionOutcomeIntelligence


class FakeS46Coordinator:
    def __init__(self):
        self.calls = 0

    def execute(self, payload):
        self.calls += 1
        return {
            "status": "COMPLETE",
            "execution_receipt_id": "R-S46-001",
            "payload": payload,
            "external_action_executed": False,
        }


def test_s46_execution_is_forwarded():
    c = FakeS46Coordinator()
    integrated = OutcomeAwareGovernedActionCoordinator(c)
    result = integrated.execute_and_observe(
        {"intent": "test"},
        project_id="P1",
        action_id="A1",
        expected="COMPLETE",
        actual="COMPLETE",
        evidence_refs=("E-S46",),
    )
    assert c.calls == 1
    assert result.execution_result["status"] == "COMPLETE"
    assert result.execution_receipt_id == "R-S46-001"


def test_s47_outcome_is_derived_from_real_receipt():
    c = FakeS46Coordinator()
    integrated = OutcomeAwareGovernedActionCoordinator(c, ExecutionOutcomeIntelligence())
    result = integrated.execute_and_observe(
        {"intent": "test"}, project_id="P1", action_id="A1",
        expected="COMPLETE", actual="COMPLETE", evidence_refs=("E-S46",)
    )
    assert result.outcome.status == "SUCCESS"
    assert result.outcome.execution_receipt_id == "R-S46-001"
    assert result.outcome.next_decision == "BOUNDED_NEXT_STEP"


def test_failure_feedback_propagates():
    c = FakeS46Coordinator()
    integrated = OutcomeAwareGovernedActionCoordinator(c)
    result = integrated.execute_and_observe(
        {"intent": "test"}, project_id="P1", action_id="A2",
        expected="COMPLETE", actual="FAILED", evidence_refs=("E-S46",)
    )
    assert result.outcome.status == "FAILURE"
    assert result.outcome.decision_feedback == "CONTRADICTS_DECISION"
    assert result.outcome.next_decision == "REASSESS_OR_CHANGE"


def test_inconclusive_remains_non_decision_driving():
    c = FakeS46Coordinator()
    integrated = OutcomeAwareGovernedActionCoordinator(c)
    result = integrated.execute_and_observe(
        {"intent": "test"}, project_id="P1", action_id="A3",
        expected="COMPLETE", actual=None, evidence_refs=("E-S46",)
    )
    assert result.outcome.status == "INCONCLUSIVE"
    assert result.outcome.learning_signal is None
    assert result.outcome.next_decision == "COLLECT_MORE_EVIDENCE"


def test_receipt_replay_is_idempotent():
    c = FakeS46Coordinator()
    engine = ExecutionOutcomeIntelligence()
    integrated = OutcomeAwareGovernedActionCoordinator(c, engine)
    first = integrated.execute_and_observe(
        {"intent": "test"}, project_id="P1", action_id="A4",
        expected="COMPLETE", actual="COMPLETE", evidence_refs=("E1",)
    )
    second = integrated.execute_and_observe(
        {"intent": "test"}, project_id="P1", action_id="A4",
        expected="COMPLETE", actual="FAILED", evidence_refs=("E2",)
    )
    assert first.execution_receipt_id == second.execution_receipt_id
    assert second.outcome == first.outcome
    assert len(engine.snapshot()) == 1


def test_external_execution_stays_blocked():
    c = FakeS46Coordinator()
    result = OutcomeAwareGovernedActionCoordinator(c).execute_and_observe(
        {"intent": "test"}, project_id="P1", action_id="A5",
        expected="COMPLETE", actual="COMPLETE", evidence_refs=("E1",)
    )
    assert result.external_action_executed is False
    assert result.memory_write_executed is False


def test_uses_existing_coordinator_method_without_reimplementing_execution():
    c = FakeS46Coordinator()
    result = OutcomeAwareGovernedActionCoordinator(c).execute_and_observe(
        {"intent": "delegated"}, project_id="P1", action_id="A6",
        expected="COMPLETE", actual="COMPLETE"
    )
    assert result.execution_result["payload"] == {"intent": "delegated"}


def test_integration_version_is_stable():
    c = FakeS46Coordinator()
    result = OutcomeAwareGovernedActionCoordinator(c).execute_and_observe(
        {"intent": "test"}, project_id="P1", action_id="A7",
        expected="COMPLETE", actual="COMPLETE"
    )
    assert result.integration_version == "O45-S48-v1"


def run_all():
    tests = [v for n, v in globals().items() if n.startswith("test_")]
    for test in tests:
        test()
    print(f"S48_TARGETED_TESTS_PASS {len(tests)}/{len(tests)}")


if __name__ == "__main__":
    run_all()
