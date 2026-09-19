import sys
sys.path.insert(0, "src")

from core.src.runtime_load_validation import run_controlled_load


def test_parallel_load_completes_without_loss():
    r = run_controlled_load(count=12, concurrency=4)
    assert r.submitted == 12
    assert r.completed == 12
    assert r.failed == 0
    assert r.peak_inflight <= 4


def test_duplicate_active_run_is_blocked_under_load():
    r = run_controlled_load(count=8, concurrency=3)
    assert r.duplicate_blocked


def test_all_runs_reach_terminal_state():
    r = run_controlled_load(count=10, concurrency=4)
    assert r.terminal_integrity


def test_bounded_concurrency_never_exceeds_configured_limit():
    r = run_controlled_load(count=20, concurrency=2)
    assert r.peak_inflight <= 2


def test_sustained_parallel_completion_has_no_failed_runs():
    r = run_controlled_load(count=24, concurrency=4)
    assert r.completed == 24
    assert r.failed == 0


def test_runner_is_dependency_free():
    r = run_controlled_load(count=6, concurrency=2)
    assert r.completed == 6


if __name__ == "__main__":
    tests = [
        test_parallel_load_completes_without_loss,
        test_duplicate_active_run_is_blocked_under_load,
        test_all_runs_reach_terminal_state,
        test_bounded_concurrency_never_exceeds_configured_limit,
        test_sustained_parallel_completion_has_no_failed_runs,
        test_runner_is_dependency_free,
    ]
    for t in tests:
        t()
    print(f"S39_TARGETED_TESTS_PASS {len(tests)}/{len(tests)}")
