from __future__ import annotations

import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from core.src.crash_recovery import CrashRecoveryController, RecoveryState


def test_interrupted_run_is_recovered():
    c = CrashRecoveryController(); c.submit("r1"); c.claim("r1", "w1", "l1")
    assert c.crash_worker("w1") == ["r1"]
    assert c.reconcile_after_restart() == ["r1"]
    assert c.records["r1"].state is RecoveryState.RECOVERED


def test_recovered_run_can_be_requeued_once():
    c = CrashRecoveryController(); c.submit("r1"); c.claim("r1", "w1", "l1"); c.crash_worker("w1"); c.reconcile_after_restart(); c.requeue_recovered("r1")
    assert c.records["r1"].state is RecoveryState.QUEUED


def test_reexecution_is_tracked_and_completes():
    c = CrashRecoveryController(); c.submit("r1"); c.claim("r1", "w1", "l1"); c.crash_worker("w1"); c.reconcile_after_restart(); c.requeue_recovered("r1"); c.claim("r1", "w2", "l2"); c.complete("r1", "hash-r1")
    rec = c.records["r1"]
    assert rec.execution_count == 2 and rec.state is RecoveryState.COMPLETE and rec.result_hash == "hash-r1"


def test_duplicate_active_run_is_blocked():
    c = CrashRecoveryController(); c.submit("r1"); c.claim("r1", "w1", "l1")
    try:
        c.submit("r1")
    except RuntimeError as exc:
        assert str(exc) == "duplicate_active_run"
    else:
        raise AssertionError("duplicate active run was not blocked")


def test_duplicate_lease_is_blocked():
    c = CrashRecoveryController(); c.submit("r1"); c.claim("r1", "w1", "l1"); c.submit("r2")
    try:
        c.claim("r2", "w2", "l1")
    except RuntimeError as exc:
        assert str(exc) == "duplicate_lease"
    else:
        raise AssertionError("duplicate lease was not blocked")


def test_close_is_idempotent():
    c = CrashRecoveryController(); c.close(); c.close()
    try:
        c.submit("r1")
    except RuntimeError as exc:
        assert str(exc) == "recovery_controller_closed"
    else:
        raise AssertionError("closed controller accepted a new run")


def main():
    tests = [v for k,v in globals().items() if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"S41_TARGETED_TESTS_PASS {len(tests)}/{len(tests)}")


if __name__ == "__main__":
    main()
