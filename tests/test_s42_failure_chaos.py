from __future__ import annotations
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from core.src.chaos_drill import run_combined_chaos

def test_combined_provider_recovery():
    r = run_combined_chaos()
    assert r["model_recovered_after_5xx"] is True

def test_combined_rate_limit_recovery():
    r = run_combined_chaos()
    assert r["search_recovered_after_429"] is True

def test_combined_runtime_bounded():
    r = run_combined_chaos()
    assert r["runtime_bounded_peak"] is True and r["peak_inflight"] <= 2

def test_combined_failure_contained():
    r = run_combined_chaos()
    assert r["runtime_failure_contained"] is True

def test_restart_interruption_reconciled():
    r = run_combined_chaos()
    assert r["recovery_detected_interruption"] is True and r["recovery_reconciled_after_restart"] is True

def test_recovery_reaches_terminal():
    r = run_combined_chaos()
    assert r["recovery_terminal_after_resume"] is True

def test_duplicate_lease_blocked():
    r = run_combined_chaos()
    assert r["duplicate_lease_blocked"] is True

def test_terminal_integrity_and_snapshot_safe():
    r = run_combined_chaos()
    assert r["runtime_terminal_integrity"] is True and r["provider_snapshot_safe"] is True

def main():
    tests = [v for k,v in globals().items() if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"S42_TARGETED_TESTS_PASS {len(tests)}/{len(tests)}")

if __name__ == "__main__":
    main()
