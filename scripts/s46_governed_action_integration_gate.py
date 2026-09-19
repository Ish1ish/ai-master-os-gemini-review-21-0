from __future__ import annotations

import json
from pathlib import Path

from core.src.action_execution_hardening import ApprovalRecord
from core.src.governed_action_integration import GovernedActionCoordinator

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "src" / "core" / "src" / "governed_action_integration.py"
HARDENING = ROOT / "src" / "core" / "src" / "action_execution_hardening.py"
TEST = ROOT / "tests" / "test_s46_governed_action_integration.py"
planner_candidates = list((ROOT / "src").rglob("execution_intent_planner.py"))

checks = {
    "integration_module_present": INTEGRATION.exists(),
    "action_hardening_present": HARDENING.exists(),
    "execution_intent_surface_present": bool(planner_candidates),
    "decision_to_intent_to_executor_path": False,
    "unauthorized_action_blocked": False,
    "approval_required": False,
    "approved_external_action_still_staged_blocked": False,
    "rejected_approval_blocked": False,
    "idempotency_preserved": False,
    "execution_receipt_present": False,
    "failure_contained": False,
    "memory_write_blocked": False,
    "targeted_tests": False,
}

coordinator = GovernedActionCoordinator()
low = coordinator.submit(project_id="P1", requester_id="operator-01", tool="formatter", action="format", capability="content:format", idempotency_key="gate-low", granted_capabilities=frozenset({"content:format"}), tool_callable=lambda _: {"ok": True})
checks["decision_to_intent_to_executor_path"] = low.governance_decision == "ALLOW" and low.status == "EXECUTED" and bool(low.intent_id)
checks["execution_receipt_present"] = bool(low.receipt.receipt_id and low.receipt.result_hash)
checks["memory_write_blocked"] = low.memory_write_executed is False

blocked = coordinator.submit(project_id="P1", requester_id="operator-01", tool="publisher", action="publish", capability="publish:public", idempotency_key="gate-deny", granted_capabilities=frozenset(), external_effect=True)
checks["unauthorized_action_blocked"] = blocked.status == "BLOCKED" and not blocked.external_action_executed

awaiting = coordinator.submit(project_id="P1", requester_id="operator-01", tool="publisher", action="publish", capability="publish:public", idempotency_key="gate-await", granted_capabilities=frozenset({"publish:public"}), external_effect=True)
checks["approval_required"] = awaiting.status == "AWAITING_APPROVAL" and awaiting.governance_decision == "APPROVAL_REQUIRED"

approval = ApprovalRecord("APR-GATE", "P1", "operator-01", "approver-01", "APPROVED", "publish:public")
staged = coordinator.submit(project_id="P1", requester_id="operator-01", tool="publisher", action="publish", capability="publish:public", idempotency_key="gate-stage", granted_capabilities=frozenset({"publish:public"}), approval=approval, external_effect=True, tool_callable=lambda _: {"published": True})
checks["approved_external_action_still_staged_blocked"] = staged.status == "BLOCKED" and not staged.external_action_executed

rejected = ApprovalRecord("APR-GATE-R", "P1", "operator-01", "approver-01", "REJECTED", "publish:public")
rejected_out = coordinator.submit(project_id="P1", requester_id="operator-01", tool="publisher", action="publish", capability="publish:public", idempotency_key="gate-reject", granted_capabilities=frozenset({"publish:public"}), approval=rejected, external_effect=True)
checks["rejected_approval_blocked"] = rejected_out.status == "BLOCKED"

first = coordinator.submit(project_id="P1", requester_id="operator-01", tool="mailer", action="draft", capability="email:draft", idempotency_key="gate-idem", granted_capabilities=frozenset({"email:draft"}), tool_callable=lambda _: {"ok": True})
second = coordinator.submit(project_id="P1", requester_id="operator-01", tool="mailer", action="draft", capability="email:draft", idempotency_key="gate-idem", granted_capabilities=frozenset({"email:draft"}), tool_callable=lambda _: {"ok": False})
checks["idempotency_preserved"] = first.receipt.receipt_id == second.receipt.receipt_id

failed = coordinator.submit(project_id="P1", requester_id="operator-01", tool="validator", action="validate", capability="qa:validate", idempotency_key="gate-fail", granted_capabilities=frozenset({"qa:validate"}), tool_callable=lambda _: (_ for _ in ()).throw(RuntimeError("boom")))
checks["failure_contained"] = failed.status == "FAILED" and not failed.external_action_executed

ns = {}
exec(compile(TEST.read_text(encoding="utf-8"), str(TEST), "exec"), ns)
ns["run_all"]()
checks["targeted_tests"] = True

status = "PASS" if all(checks.values()) else "FAIL"
print("S46_GOVERNED_ACTION_INTEGRATION_" + status)
print(json.dumps({
    "release": "O45-S46",
    "status": status,
    "checks": checks,
    "external_action_executed": False,
    "memory_write_executed": False,
    "internet_facing_production_approval": False,
    "notes": [k for k, v in checks.items() if not v],
}, indent=2))
