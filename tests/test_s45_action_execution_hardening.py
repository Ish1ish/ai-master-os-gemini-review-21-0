from __future__ import annotations

from core.src.action_execution_hardening import (
    ApprovalRecord,
    GovernanceDecision,
    HardenedActionExecutor,
    build_action_intent,
    evaluate_governance,
)


def test_capability_denial():
    intent = build_action_intent(project_id="P1", requester_id="u1", tool="mailer", action="send", capability="message:send", idempotency_key="k1")
    assert evaluate_governance(intent, granted_capabilities=frozenset(), approval=None) is GovernanceDecision.BLOCK


def test_low_risk_allow():
    intent = build_action_intent(project_id="P1", requester_id="u1", tool="search", action="read", capability="search:read", idempotency_key="k2")
    assert evaluate_governance(intent, granted_capabilities=frozenset({"search:read"}), approval=None) is GovernanceDecision.ALLOW


def test_high_impact_requires_approval():
    intent = build_action_intent(project_id="P1", requester_id="u1", tool="publisher", action="publish", capability="publish:public", idempotency_key="k3", external_effect=True)
    assert evaluate_governance(intent, granted_capabilities=frozenset({"publish:public"}), approval=None) is GovernanceDecision.APPROVAL_REQUIRED


def test_self_approval_blocked():
    intent = build_action_intent(project_id="P1", requester_id="u1", tool="publisher", action="publish", capability="publish:public", idempotency_key="k4", external_effect=True)
    approval = ApprovalRecord("A1", "P1", "u1", "u1", "APPROVED", "publish:public")
    assert evaluate_governance(intent, granted_capabilities=frozenset({"publish:public"}), approval=approval) is GovernanceDecision.BLOCK


def test_approved_external_still_disabled():
    intent = build_action_intent(project_id="P1", requester_id="u1", tool="publisher", action="publish", capability="publish:public", idempotency_key="k5", external_effect=True)
    approval = ApprovalRecord("A2", "P1", "u1", "approver-1", "APPROVED", "publish:public")
    executor = HardenedActionExecutor()
    receipt = executor.execute(intent, granted_capabilities=frozenset({"publish:public"}), approval=approval, tool=lambda _: {"ok": True})
    assert receipt.status == "BLOCKED"
    assert receipt.external_action_executed is False


def test_idempotency_returns_same_receipt():
    intent = build_action_intent(project_id="P1", requester_id="u1", tool="email", action="draft", capability="email:draft", idempotency_key="same")
    executor = HardenedActionExecutor()
    first = executor.execute(intent, granted_capabilities=frozenset({"email:draft"}), tool=lambda _: {"draft": True})
    second = executor.execute(intent, granted_capabilities=frozenset({"email:draft"}), tool=lambda _: {"draft": False})
    assert first.receipt_id == second.receipt_id
    assert len(executor.snapshot()) == 1


def test_execution_receipt_records_outcome():
    intent = build_action_intent(project_id="P1", requester_id="u1", tool="formatter", action="format", capability="content:format", idempotency_key="r1")
    executor = HardenedActionExecutor()
    receipt = executor.execute(intent, granted_capabilities=frozenset({"content:format"}), tool=lambda _: {"formatted": True})
    assert receipt.status == "EXECUTED"
    assert receipt.tool_invoked is True
    assert receipt.result_hash


def test_fail_closed_on_tool_error():
    intent = build_action_intent(project_id="P1", requester_id="u1", tool="x", action="run", capability="x:run", idempotency_key="err1")
    executor = HardenedActionExecutor()
    def boom(_):
        raise RuntimeError("boom")
    receipt = executor.execute(intent, granted_capabilities=frozenset({"x:run"}), tool=boom)
    assert receipt.status == "FAILED"
    assert receipt.external_action_executed is False


def run_all():
    tests = [v for n, v in globals().items() if n.startswith("test_")]
    for test in tests:
        test()
    print(f"S45_TARGETED_TESTS_PASS {len(tests)}/{len(tests)}")


if __name__ == "__main__":
    run_all()
