from __future__ import annotations
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from core.src.security_abuse_drill import run_security_abuse_drill

def test_missing_token_rejected():
    assert run_security_abuse_drill()["missing_token_rejected"]

def test_malformed_token_rejected():
    assert run_security_abuse_drill()["malformed_token_rejected"]

def test_scope_escalation_denied():
    assert run_security_abuse_drill()["scope_escalation_denied"]

def test_cross_tenant_access_denied():
    assert run_security_abuse_drill()["cross_tenant_access_denied"]

def test_tenant_owner_mismatch_denied():
    assert run_security_abuse_drill()["tenant_owner_mismatch_denied"]

def test_replay_blocked():
    assert run_security_abuse_drill()["replay_request_blocked"]

def test_valid_access_allowed():
    assert run_security_abuse_drill()["valid_scoped_access_allowed"]

def test_admin_override_explicit():
    assert run_security_abuse_drill()["admin_scope_override_explicit"]

def main():
    tests = [v for k,v in globals().items() if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"S43_TARGETED_TESTS_PASS {len(tests)}/{len(tests)}")

if __name__ == "__main__":
    main()
