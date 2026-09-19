from __future__ import annotations

from core.src.real_provider_failure_recovery import (
    BoundedProviderRecovery,
    RealProviderFailureRecoveryCoordinator,
)


def fake_model(prompt):
    return {"provider": "fake-model", "model": "test-model", "text": "PROVIDER_OK"}


def fake_search(query):
    return {"results": [{"title": "test", "snippet": "evidence"}]}


def make(**kwargs):
    return RealProviderFailureRecoveryCoordinator(
        model=fake_model,
        search=fake_search,
        **kwargs,
    )


def test_transient_model_failure_recovers():
    out = make(model_failures=1, search_failures=0).run()
    assert out.injected_model_failures == 1
    assert out.model_attempts >= 3
    assert len(out.closed_loop.closed_loop.cycles) == 2


def test_transient_search_failure_recovers():
    out = make(model_failures=0, search_failures=1).run()
    assert out.injected_search_failures == 1
    assert out.search_attempts >= 3
    assert len(out.closed_loop.closed_loop.cycles) == 2


def test_both_transient_failures_recover():
    out = make(model_failures=1, search_failures=1).run()
    assert out.injected_model_failures == 1
    assert out.injected_search_failures == 1
    assert out.model_attempts >= 3
    assert out.search_attempts >= 3
    assert all(c.execution_status == "EXECUTED" for c in out.closed_loop.closed_loop.cycles)


def test_two_cycles_preserved_after_recovery():
    out = make(model_failures=1, search_failures=1).run()
    cycles = out.closed_loop.closed_loop.cycles
    assert len(cycles) == 2
    assert cycles[0].trace_id != cycles[1].trace_id


def test_reentry_survives_recovery():
    out = make(model_failures=1, search_failures=1).run()
    assert all(c.reentry.next_decision == c.next_decision for c in out.closed_loop.closed_loop.cycles)


def test_side_effects_remain_blocked():
    out = make(model_failures=1, search_failures=1).run()
    assert out.external_action_executed is False
    assert out.memory_write_executed is False
    assert out.closed_loop.closed_loop.execution_triggered is False


def test_retry_exhaustion_fails_closed():
    def always_fail(prompt):
        raise RuntimeError("persistent_model_failure")

    coordinator = RealProviderFailureRecoveryCoordinator(
        model=always_fail,
        search=fake_search,
        model_failures=0,
        search_failures=0,
        max_attempts=2,
    )
    try:
        coordinator.run()
    except RuntimeError as exc:
        assert "recovery_exhausted" in str(exc)
    else:
        raise AssertionError("persistent provider failure did not fail closed")


def test_invalid_retry_budget_rejected():
    try:
        BoundedProviderRecovery(max_attempts=0)
    except ValueError:
        return
    raise AssertionError("invalid retry budget accepted")


def test_no_auto_execution_after_reentry():
    out = make(model_failures=1, search_failures=1).run()
    assert all(c.execution_triggered is False for c in out.closed_loop.closed_loop.cycles)


def test_governed_result_remains_complete():
    out = make(model_failures=1, search_failures=1).run()
    assert all(c.outcome_status == "SUCCESS" for c in out.closed_loop.closed_loop.cycles)


def test_failure_injection_is_bounded():
    out = make(model_failures=1, search_failures=1, max_attempts=2).run()
    assert out.injected_model_failures == 1
    assert out.injected_search_failures == 1
    assert out.model_attempts == 3
    assert out.search_attempts == 3


def test_recovery_wrapper_only_retries_bounded_calls():
    calls = {"n": 0}

    def fail_once(value):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("once")
        return {"ok": True}

    wrapped = BoundedProviderRecovery(max_attempts=2).wrap("model", fail_once)
    assert wrapped("x")["ok"] is True
    assert calls["n"] == 2


def run_all():
    tests = [v for n, v in globals().items() if n.startswith("test_")]
    for test in tests:
        test()
    print(f"S53_TARGETED_TESTS_PASS {len(tests)}/{len(tests)}")


if __name__ == "__main__":
    run_all()
