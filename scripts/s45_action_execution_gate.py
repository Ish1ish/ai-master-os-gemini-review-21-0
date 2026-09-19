from __future__ import annotations

import json
from pathlib import Path

from core.src.action_execution_hardening import HardenedActionExecutor, build_action_intent

ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "src" / "core" / "src"
HARDENING = CORE_SRC / "action_execution_hardening.py"
TEST = ROOT / "tests" / "test_s45_action_execution_hardening.py"

checks = {
    "execution_intent_contract_surface": callable(build_action_intent),
    "action_hardening_present": HARDENING.exists(),
    "capability_boundary": False,
    "approval_required_for_consequential_action": False,
    "approved_external_action_still_staged_blocked": False,
    "idempotency_receipt": False,
    "execution_receipt_present": False,
    "failure_contained": False,
    "targeted_tests": False,
}

intent = build_action_intent(project_id="P1", requester_id="u1", tool="publisher", action="publish", capability="publish:public", idempotency_key="gate-1", external_effect=True)
executor = HardenedActionExecutor()
blocked = executor.execute(intent, granted_capabilities=frozenset(), approval=None)
checks["capability_boundary"] = blocked.status == "BLOCKED"

approval = __import__("core.src.action_execution_hardening", fromlist=["ApprovalRecord"]).ApprovalRecord("A1", "P1", "u1", "approver-1", "APPROVED", "publish:public")
awaiting = HardenedActionExecutor().execute(intent, granted_capabilities=frozenset({"publish:public"}), approval=None)
checks["approval_required_for_consequential_action"] = awaiting.status == "AWAITING_APPROVAL"

staged = executor.execute(intent, granted_capabilities=frozenset({"publish:public"}), approval=approval)
checks["approved_external_action_still_staged_blocked"] = staged.status == "BLOCKED" and not staged.external_action_executed

low = build_action_intent(project_id="P1", requester_id="u1", tool="formatter", action="format", capability="content:format", idempotency_key="idem-1")
first = executor.execute(low, granted_capabilities=frozenset({"content:format"}), tool=lambda _: {"ok": True})
second = executor.execute(low, granted_capabilities=frozenset({"content:format"}), tool=lambda _: {"ok": False})
checks["idempotency_receipt"] = first.receipt_id == second.receipt_id
checks["execution_receipt_present"] = bool(first.receipt_id and first.result_hash and first.status == "EXECUTED")

fail = build_action_intent(project_id="P1", requester_id="u1", tool="x", action="run", capability="x:run", idempotency_key="err-gate")
failed = executor.execute(fail, granted_capabilities=frozenset({"x:run"}), tool=lambda _: (_ for _ in ()).throw(RuntimeError("boom")))
checks["failure_contained"] = failed.status == "FAILED" and not failed.external_action_executed

ns = {}
exec(compile(TEST.read_text(encoding="utf-8"), str(TEST), "exec"), ns)
ns["run_all"]()
checks["targeted_tests"] = True

status = "PASS" if all(checks.values()) else "FAIL"
print("S45_ACTION_EXECUTION_HARDENING_" + status)
print(json.dumps({
    "release": "O45-S45",
    "status": status,
    "checks": checks,
    "external_action_executed": False,
    "memory_write_executed": False,
    "internet_facing_production_approval": False,
    "notes": [k for k, v in checks.items() if not v],
}, indent=2))
