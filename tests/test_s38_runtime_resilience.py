
import sys, threading, time
sys.path.insert(0, "src")
from core.src.runtime_resilience import ResilientRuntime, ResilienceConfig, RunState

def test_bounded_concurrency():
    r = ResilientRuntime(ResilienceConfig(max_workers=4, max_inflight_runs=2))
    barrier = threading.Barrier(2)
    def work():
        barrier.wait(timeout=2); time.sleep(0.08); return "ok"
    fs=[]
    for i in range(2): fs.append(r.submit(f"r{i}", work))
    assert [f.result(timeout=2) for f in fs] == ["ok","ok"]
    assert r.admission.peak_inflight == 2
    r.close()

def test_admission_rejects_excess_without_overcommit():
    r = ResilientRuntime(ResilienceConfig(max_workers=2, max_inflight_runs=1))
    started = threading.Event(); release = threading.Event()
    def work():
        started.set(); release.wait(timeout=2); return "ok"
    f = r.submit("busy", work); assert started.wait(2)
    try:
        r.submit("overflow", lambda: "bad")
        assert False, "expected admission rejection"
    except RuntimeError as e:
        assert str(e) == "concurrency_admission_rejected"
    release.set(); assert f.result(timeout=2) == "ok"
    assert r.admission.inflight == 0 and r.admission.peak_inflight == 1
    r.close()

def test_failure_is_terminal_and_recorded():
    r = ResilientRuntime()
    f = r.submit("boom", lambda: (_ for _ in ()).throw(ValueError("provider failed")))
    try: f.result(timeout=2)
    except ValueError: pass
    rec = r.record("boom")
    assert rec.state is RunState.FAILED
    assert "ValueError" in rec.error
    r.close()

def test_duplicate_active_run_is_blocked():
    r = ResilientRuntime(ResilienceConfig(max_inflight_runs=1))
    release = threading.Event()
    f = r.submit("same", lambda: (release.wait(2), "ok")[1])
    try:
        r.submit("same", lambda: "bad")
        assert False, "expected duplicate block"
    except RuntimeError as e:
        assert str(e) == "duplicate_active_run"
    release.set(); assert f.result(timeout=2) == "ok"
    r.close()

def test_close_is_idempotent_and_new_submit_fails_closed():
    r = ResilientRuntime(); r.close(); r.close()
    try:
        r.submit("after-close", lambda: "bad")
        assert False, "expected runtime_closed"
    except RuntimeError as e:
        assert str(e) == "runtime_closed"

if __name__ == "__main__":
    tests=[test_bounded_concurrency,test_admission_rejects_excess_without_overcommit,test_failure_is_terminal_and_recorded,test_duplicate_active_run_is_blocked,test_close_is_idempotent_and_new_submit_fails_closed]
    for t in tests: t()
    print(f"S38_TARGETED_TESTS_PASS {len(tests)}/{len(tests)}")
