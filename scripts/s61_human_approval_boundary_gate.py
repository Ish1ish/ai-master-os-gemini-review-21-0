from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    module = root / "src/core/src/human_approval_boundary.py"
    test = root / "tests/test_o46_human_approval_boundary.py"
    checks = {
        "module_present": module.exists(),
        "targeted_tests_present": test.exists(),
        "explicit_consequential_state": False,
        "auto_approval_blocked": False,
        "rejection_blocks_release": False,
        "explicit_approval_releases": False,
        "approval_idempotent": False,
        "external_action_not_executed": False,
        "compileall": False,
    }
    env = dict(__import__("os").environ)
    env["PYTHONPATH"] = str(root / "src")

    test_run = subprocess.run(
        [sys.executable, str(test)], cwd=root, capture_output=True, text=True, env=env
    )
    checks["targeted_tests"] = test_run.returncode == 0 and "S61_TARGETED_TESTS_PASS 15/15" in test_run.stdout

    compile_run = subprocess.run(
        [sys.executable, "-m", "compileall", "-q", "src", "tests"],
        cwd=root, capture_output=True, text=True, env=env,
    )
    checks["compileall"] = compile_run.returncode == 0

    boundary_snapshot = {}
    try:
        sys.path.insert(0, str(root / "src"))
        from core.src.human_approval_boundary import ActionRisk, ApprovalState, HumanApprovalBoundary

        gate = HumanApprovalBoundary()
        req = gate.request(
            action_id="S61-GATE-ACTION",
            action_type="external_publish",
            risk=ActionRisk.CONSEQUENTIAL,
            summary="Gate validation action",
        )
        checks["explicit_consequential_state"] = req.state == ApprovalState.AWAITING_APPROVAL
        checks["auto_approval_blocked"] = gate.can_release_external(req.action_id) is False
        rejected = gate.reject(action_id=req.action_id, approver_id="gate-human", reason="test rejection")
        checks["rejection_blocks_release"] = rejected.released is False and gate.can_release_external(req.action_id) is False

        req2 = gate.request(
            action_id="S61-GATE-ACTION-2",
            action_type="external_message",
            risk=ActionRisk.CONSEQUENTIAL,
            summary="Gate validation approval",
        )
        approved = gate.approve(action_id=req2.action_id, approver_id="gate-human")
        approved_again = gate.approve(action_id=req2.action_id, approver_id="gate-human")
        boundary_snapshot = gate.snapshot()
        checks["external_action_not_executed"] = (
            rejected.released is False
            and approved.external_action_executed is False
            and boundary_snapshot.get("external_action_executed") is False
        )
        checks["explicit_approval_releases"] = approved.state == ApprovalState.APPROVED and approved.released
        checks["approval_idempotent"] = approved_again.decision_fingerprint == approved.decision_fingerprint
    except Exception as exc:
        print(f"gate_runtime_error={type(exc).__name__}:{exc}")

    status = "PASS" if all(checks.values()) else "FAIL"
    payload = {
        "release": "O46-S61",
        "status": status,
        "checks": checks,
        "path": "O46 consequential intent -> explicit human approval boundary -> await/reject/approve -> release to downstream executor",
        "external_action_executed": boundary_snapshot.get("external_action_executed") if boundary_snapshot else None,
        "automatic_approval": False,
        "notes": [
            "Approval releases the action to a downstream executor; this boundary itself never performs an external action.",
            "S61 does not claim runtime evidence for memory writes; that concern is covered by downstream integration gates.",
        ],
    }
    print("S61_HUMAN_APPROVAL_BOUNDARY_PASS" if status == "PASS" else "S61_HUMAN_APPROVAL_BOUNDARY_FAIL")
    print(json.dumps(payload, indent=2))
    print(test_run.stdout, end="")
    print(test_run.stderr, end="")
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
