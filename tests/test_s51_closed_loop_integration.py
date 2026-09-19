from __future__ import annotations

from core.src.closed_loop_integration import FullClosedLoopCoordinator


def make():
    return FullClosedLoopCoordinator()


def test_real_s46_execution_completes():
    out = make().run_two_cycles()
    assert out.cycles[0].execution_status == "EXECUTED"


def test_s47_outcome_is_success():
    out = make().run_two_cycles()
    assert out.cycles[0].outcome_status == "SUCCESS"


def test_s49_trace_exists():
    c = make(); out = c.run_two_cycles()
    assert len(c.trace_snapshot()) == 2
    assert all(any(t.trace_id == x for t in c.trace_snapshot().values()) for x in out.trace_ids)


def test_s50_reentry_exists():
    c = make(); out = c.run_two_cycles()
    assert len(c.reentry_snapshot()) == 2
    assert all(x in c.reentry_snapshot() for x in out.reentry_ids)


def test_next_decision_crosses_full_boundary():
    out = make().run_two_cycles()
    assert out.cycles[0].next_decision == "BOUNDED_NEXT_STEP"
    assert out.cycles[0].reentry.next_decision == out.cycles[0].next_decision


def test_second_cycle_is_a_new_execution():
    out = make().run_two_cycles()
    assert out.cycles[0].execution_receipt_id != out.cycles[1].execution_receipt_id
    assert out.trace_ids[0] != out.trace_ids[1]


def test_second_cycle_carries_first_reentry_context():
    out = make().run_two_cycles()
    assert out.cycles[1].reentry.source_trace_id == out.cycles[1].trace_id
    assert out.cycles[1].execution_receipt_id != out.cycles[0].execution_receipt_id


def test_no_external_action():
    out = make().run_two_cycles()
    assert out.external_action_executed is False
    assert all(not x.external_action_executed for x in out.cycles)


def test_no_memory_write():
    out = make().run_two_cycles()
    assert out.memory_write_executed is False
    assert all(not x.memory_write_executed for x in out.cycles)


def test_reentry_does_not_execute_automatically():
    out = make().run_two_cycles()
    assert out.execution_triggered is False
    assert all(not x.execution_triggered for x in out.cycles)


def test_idempotent_reentry_and_trace():
    c = make()
    first = c.run_cycle(project_id="P-S51-I", action_id="A1", idempotency_key="K1", payload={"x":1}, evidence_refs=("E1",))
    again = c.reentry.reenter_from_receipt(first.execution_receipt_id)
    assert again is not None
    assert again.context == first.reentry
    assert len(c.trace_snapshot()) == 1
    assert len(c.reentry_snapshot()) == 1


def test_evidence_is_traceable():
    c = make(); out = c.run_two_cycles()
    trace = next(t for t in c.trace_snapshot().values() if t.trace_id == out.trace_ids[0])
    assert trace.evidence_refs == ("E-S51-1", "E-S51-2")


def test_production_approval_remains_blocked():
    out = make().run_two_cycles()
    assert out.external_action_executed is False
    assert out.memory_write_executed is False


def run_all():
    tests = [v for n, v in globals().items() if n.startswith("test_")]
    for test in tests:
        test()
    print(f"S51_TARGETED_TESTS_PASS {len(tests)}/{len(tests)}")


if __name__ == "__main__":
    run_all()
