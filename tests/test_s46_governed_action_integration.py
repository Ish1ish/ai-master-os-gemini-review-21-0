from __future__ import annotations

from core.src.action_execution_hardening import ApprovalRecord
from core.src.governed_action_integration import GovernedActionCoordinator


def test_low_risk_action_reaches_executor():
    c = GovernedActionCoordinator()
    out = c.submit(project_id="P1", requester_id="operator-01", tool="formatter", action="format", capability="content:format", idempotency_key="low", granted_capabilities=frozenset({"content:format"}), tool_callable=lambda _: {"ok": True})
    assert out.status == "EXECUTED" and out.governance_decision == "ALLOW" and out.receipt.result_hash


def test_consequential_action_requires_approval():
    c = GovernedActionCoordinator()
    out = c.submit(project_id="P1", requester_id="operator-01", tool="publisher", action="publish", capability="publish:public", idempotency_key="await", granted_capabilities=frozenset({"publish:public"}), external_effect=True)
    assert out.status == "AWAITING_APPROVAL" and out.governance_decision == "APPROVAL_REQUIRED"


def test_approved_consequential_action_stays_staged_blocked():
    c = GovernedActionCoordinator()
    approval = ApprovalRecord("APR-1", "P1", "operator-01", "approver-01", "APPROVED", "publish:public")
    calls = {"n": 0}
    def publish(_):
        calls["n"] += 1
        return {"published": True}
    out = c.submit(project_id="P1", requester_id="operator-01", tool="publisher", action="publish", capability="publish:public", idempotency_key="stage", granted_capabilities=frozenset({"publish:public"}), approval=approval, external_effect=True, tool_callable=publish)
    assert out.status == "BLOCKED" and not out.external_action_executed and calls["n"] == 0


def test_rejected_approval_is_blocked():
    c = GovernedActionCoordinator()
    approval = ApprovalRecord("APR-2", "P1", "operator-01", "approver-01", "REJECTED", "publish:public")
    out = c.submit(project_id="P1", requester_id="operator-01", tool="publisher", action="publish", capability="publish:public", idempotency_key="reject", granted_capabilities=frozenset({"publish:public"}), approval=approval, external_effect=True)
    assert out.status == "BLOCKED" and out.governance_decision == "BLOCK"


def test_duplicate_idempotency_returns_same_receipt():
    c = GovernedActionCoordinator()
    calls = {"n": 0}
    def tool(_):
        calls["n"] += 1
        return {"ok": True}
    first = c.submit(project_id="P1", requester_id="operator-01", tool="mailer", action="draft", capability="email:draft", idempotency_key="idem", granted_capabilities=frozenset({"email:draft"}), tool_callable=tool)
    second = c.submit(project_id="P1", requester_id="operator-01", tool="mailer", action="draft", capability="email:draft", idempotency_key="idem", granted_capabilities=frozenset({"email:draft"}), tool_callable=lambda _: {"ok": False})
    assert first.receipt.receipt_id == second.receipt.receipt_id and calls["n"] == 1 and len(c.snapshot()) == 1


def test_unauthorized_action_never_reaches_tool():
    c = GovernedActionCoordinator()
    calls = {"n": 0}
    def tool(_):
        calls["n"] += 1
        return {"ok": True}
    out = c.submit(project_id="P1", requester_id="operator-01", tool="shell", action="run", capability="shell:execute", idempotency_key="deny", granted_capabilities=frozenset(), tool_callable=tool)
    assert out.status == "BLOCKED" and calls["n"] == 0


def test_failure_is_contained_and_receipted():
    c = GovernedActionCoordinator()
    def boom(_):
        raise RuntimeError("simulated_failure")
    out = c.submit(project_id="P1", requester_id="operator-01", tool="validator", action="validate", capability="qa:validate", idempotency_key="fail", granted_capabilities=frozenset({"qa:validate"}), tool_callable=boom)
    assert out.status == "FAILED" and out.receipt.failure_reason == "RuntimeError" and not out.external_action_executed


def test_memory_write_never_occurs_at_boundary():
    c = GovernedActionCoordinator()
    out = c.submit(project_id="P1", requester_id="operator-01", tool="audit", action="record", capability="audit:write", idempotency_key="audit", granted_capabilities=frozenset({"audit:write"}), tool_callable=lambda _: {"recorded": True})
    assert out.memory_write_executed is False


def run_all():
    tests = [v for n, v in globals().items() if n.startswith("test_")]
    for test in tests:
        test()
    print(f"S46_TARGETED_TESTS_PASS {len(tests)}/{len(tests)}")


if __name__ == "__main__":
    run_all()
