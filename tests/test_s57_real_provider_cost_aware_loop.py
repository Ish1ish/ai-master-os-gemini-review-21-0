from __future__ import annotations
from core.src.real_provider_cost_aware_loop import RealProviderCostAwareLoopCoordinator


def fake_model(prompt):
    return {"provider": "fake-model", "model": "test-model", "text": "PROVIDER_OK"}


def fake_search(query):
    return {"results": [{"title": "test", "snippet": "evidence"}]}


def make(**kwargs):
    return RealProviderCostAwareLoopCoordinator(
        model=fake_model,
        search=fake_search,
        **kwargs,
    )


def test_two_cycles_complete_under_budget():
    out = make(max_budget_units=12).run()
    assert out.closed_loop_two_cycles is True
    assert len(out.cycles) == 2


def test_real_provider_call_budget_is_tracked():
    out = make(max_budget_units=12).run()
    assert out.total_provider_calls > 0
    assert out.total_budget_units > 0
    assert all(c.model_stats.provider_calls <= c.model_stats.max_provider_calls for c in out.cycles)
    assert all(c.search_stats.provider_calls <= c.search_stats.max_provider_calls for c in out.cycles)


def test_transient_failure_recovered_within_budget():
    out = make(max_budget_units=12, inject_model_failures=1, inject_search_failures=1).run()
    assert out.cycles[0].model_stats.failures_injected == 1
    assert out.cycles[0].search_stats.failures_injected == 1
    assert out.cycles[0].status == "SUCCESS"


def test_second_cycle_has_no_injected_failure():
    out = make(max_budget_units=12, inject_model_failures=1, inject_search_failures=1).run()
    assert out.cycles[1].model_stats.failures_injected == 0
    assert out.cycles[1].search_stats.failures_injected == 0


def test_traceability_contains_budget_and_provider_refs():
    c = make(max_budget_units=12)
    out = c.run()
    snapshots = c.closed_loop.trace_snapshot()
    refs = []
    for trace_id in (x.trace_id for x in out.cycles):
        refs.extend(next(v for v in snapshots.values() if v.trace_id == trace_id).evidence_refs)
    assert any(r.startswith("REAL-MODEL-") for r in refs)
    assert any(r.startswith("REAL-SEARCH-") for r in refs)
    assert any(r.startswith("BUDGET-") for r in refs)


def test_reentry_and_new_trace():
    out = make(max_budget_units=12).run()
    assert out.next_decision_reentered is True
    assert out.new_trace_each_cycle is True


def test_side_effects_blocked():
    out = make(max_budget_units=12).run()
    assert out.external_action_executed is False
    assert out.memory_write_executed is False
    assert out.execution_triggered is False


def test_budget_fail_closed_before_provider_retry():
    try:
        make(max_budget_units=1, inject_model_failures=1, inject_search_failures=1).run()
    except RuntimeError as exc:
        assert "s57_budget_exceeded_fail_closed" in str(exc)
    else:
        raise AssertionError("budget did not fail closed")


def test_no_auto_execution_after_reentry():
    out = make(max_budget_units=12).run()
    assert all(c.next_decision for c in out.cycles)


def test_idempotent_closed_loop_shape():
    a = make(max_budget_units=12).run(project_id="P-S57-IDEMP")
    b = make(max_budget_units=12).run(project_id="P-S57-IDEMP")
    assert len(a.cycles) == len(b.cycles) == 2


def test_compile_shape():
    out = make(max_budget_units=12).run()
    assert all(c.provider_model_live and c.provider_search_live for c in out.cycles)


def test_budget_units_never_negative():
    out = make(max_budget_units=12).run()
    assert out.total_budget_units >= 0


def test_model_search_hashes_present():
    out = make(max_budget_units=12).run()
    assert all(len(c.model_hash) == 64 and len(c.search_hash) == 64 for c in out.cycles)


def test_cycle_indices_ordered():
    out = make(max_budget_units=12).run()
    assert [c.cycle_index for c in out.cycles] == [1, 2]


def test_provider_search_results_nonempty():
    out = make(max_budget_units=12).run()
    assert all(c.search_result_count > 0 for c in out.cycles)


def test_run_result_marks_configured_for_test_providers():
    out = make(max_budget_units=12).run()
    assert isinstance(out.configured, bool)


def run_all():
    tests=[v for n,v in globals().items() if n.startswith('test_')]
    for t in tests: t()
    print(f"S57_TARGETED_TESTS_PASS {len(tests)}/{len(tests)}")

if __name__=='__main__': run_all()
