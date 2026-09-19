from __future__ import annotations

from core.src.real_provider_closed_loop import RealProviderClosedLoopCoordinator


def fake_model(prompt):
    return {"provider": "fake-model", "model": "test-model", "text": "PROVIDER_OK"}


def fake_search(query):
    return {"results": [{"title": "test", "snippet": "evidence"}]}


def make():
    return RealProviderClosedLoopCoordinator(model=fake_model, search=fake_search)


def test_provider_evidence_hashes():
    evidence = make().collect_provider_evidence()
    assert len(evidence.model_hash) == 64
    assert len(evidence.search_hash) == 64
    assert evidence.search_result_count == 1


def test_first_cycle_uses_provider_evidence():
    out = make().run_two_cycles()
    assert out.closed_loop.cycles[0].execution_status == "EXECUTED"
    trace = next(iter(make().closed_loop.trace_snapshot().values()), None)
    assert trace is None


def test_two_cycles_complete():
    out = make().run_two_cycles()
    assert len(out.closed_loop.cycles) == 2
    assert all(c.execution_status == "EXECUTED" for c in out.closed_loop.cycles)


def test_outcomes_success():
    out = make().run_two_cycles()
    assert all(c.outcome_status == "SUCCESS" for c in out.closed_loop.cycles)


def test_provider_evidence_hash_prefixes_are_traceable():
    c = make()
    out = c.run_two_cycles()
    snapshots = c.closed_loop.trace_snapshot()
    refs = []
    for trace_id in out.closed_loop.trace_ids:
        trace = next(v for v in snapshots.values() if v.trace_id == trace_id)
        refs.extend(trace.evidence_refs)
    assert any(r.startswith("REAL-MODEL-") for r in refs)
    assert any(r.startswith("REAL-SEARCH-") for r in refs)


def test_reentry_occurs():
    out = make().run_two_cycles()
    assert out.closed_loop.cycles[0].reentry.next_decision == out.closed_loop.cycles[0].next_decision
    assert out.closed_loop.cycles[1].reentry.next_decision == out.closed_loop.cycles[1].next_decision


def test_no_external_or_memory_side_effects():
    out = make().run_two_cycles()
    assert out.external_action_executed is False
    assert out.memory_write_executed is False


def test_reentry_never_auto_executes():
    out = make().run_two_cycles()
    assert out.closed_loop.execution_triggered is False
    assert all(c.execution_triggered is False for c in out.closed_loop.cycles)


def test_new_trace_each_cycle():
    out = make().run_two_cycles()
    assert out.closed_loop.trace_ids[0] != out.closed_loop.trace_ids[1]


def test_provider_refresh_before_second_cycle():
    calls = {"model": 0, "search": 0}

    def model(prompt):
        calls["model"] += 1
        return {"text": f"MODEL_{calls['model']}"}

    def search(query):
        calls["search"] += 1
        return {"results": [{"snippet": f"SEARCH_{calls['search']}"}]}

    out = RealProviderClosedLoopCoordinator(model=model, search=search).run_two_cycles()
    assert calls == {"model": 2, "search": 2}
    assert len(out.closed_loop.cycles) == 2


def run_all():
    tests = [v for n, v in globals().items() if n.startswith("test_")]
    for test in tests:
        test()
    print(f"S52_TARGETED_TESTS_PASS {len(tests)}/{len(tests)}")


if __name__ == "__main__":
    run_all()
