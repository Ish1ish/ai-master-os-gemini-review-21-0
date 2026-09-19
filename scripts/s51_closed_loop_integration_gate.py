from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    source = root / "src" / "core" / "src" / "closed_loop_integration.py"
    tests = root / "tests" / "test_s51_closed_loop_integration.py"
    deps = {
        "s46": root / "src" / "core" / "src" / "governed_action_integration.py",
        "s47": root / "src" / "core" / "src" / "execution_outcome_intelligence.py",
        "s48": root / "src" / "core" / "src" / "execution_outcome_integration.py",
        "s49": root / "src" / "core" / "src" / "execution_outcome_persistence.py",
        "s50": root / "src" / "core" / "src" / "decision_loop_reentry.py",
    }
    checks = {k + "_present": v.exists() for k, v in deps.items()}
    checks["s51_integration_present"] = source.exists()
    checks["targeted_tests_present"] = tests.exists()

    if source.exists():
        tree = ast.parse(source.read_text(encoding="utf-8"))
        classes = {n.name for n in tree.body if isinstance(n, ast.ClassDef)}
        checks["closed_loop_coordinator_present"] = "FullClosedLoopCoordinator" in classes
        checks["closed_loop_cycle_result_present"] = "ClosedLoopCycleResult" in classes
        checks["closed_loop_result_present"] = "ClosedLoopResult" in classes
    else:
        checks["closed_loop_coordinator_present"] = False
        checks["closed_loop_cycle_result_present"] = False
        checks["closed_loop_result_present"] = False

    proc = subprocess.run([sys.executable, str(tests)], cwd=str(root), capture_output=True, text=True)
    checks["targeted_tests"] = proc.returncode == 0 and "S51_TARGETED_TESTS_PASS 13/13" in proc.stdout
    compile_proc = subprocess.run([sys.executable, "-m", "compileall", "-q", "src", "tests"], cwd=str(root))
    checks["compileall"] = compile_proc.returncode == 0

    try:
        if checks["targeted_tests"]:
            sys.path.insert(0, str(root / "src"))
            from core.src.closed_loop_integration import FullClosedLoopCoordinator
            result = FullClosedLoopCoordinator().run_two_cycles()
            checks["s46_to_s50_closed_loop"] = len(result.cycles) == 2
            checks["cycle_1_complete"] = result.cycles[0].execution_status == "EXECUTED"
            checks["cycle_2_complete"] = result.cycles[1].execution_status == "EXECUTED"
            checks["next_decision_reentered"] = all(c.reentry.next_decision == c.next_decision for c in result.cycles)
            checks["new_trace_each_cycle"] = result.trace_ids[0] != result.trace_ids[1]
            checks["reentry_is_idempotent"] = len(FullClosedLoopCoordinator().reentry_snapshot()) == 0
            checks["external_action_blocked"] = result.external_action_executed is False
            checks["memory_write_blocked"] = result.memory_write_executed is False
            checks["execution_not_triggered_by_reentry"] = result.execution_triggered is False and all(not c.execution_triggered for c in result.cycles)
        else:
            raise RuntimeError("targeted tests did not pass")
    except Exception as exc:
        checks.update({
            "s46_to_s50_closed_loop": False,
            "cycle_1_complete": False,
            "cycle_2_complete": False,
            "next_decision_reentered": False,
            "new_trace_each_cycle": False,
            "reentry_is_idempotent": False,
            "external_action_blocked": False,
            "memory_write_blocked": False,
            "execution_not_triggered_by_reentry": False,
        })
        notes = [f"gate_runtime_error={type(exc).__name__}:{exc}"]
    else:
        notes = ["S51 composes the verified S46-S50 boundaries into two deterministic local cycles; re-entry does not auto-execute the next action."]

    status = "PASS" if all(checks.values()) else "FAIL"
    print("S51_CLOSED_LOOP_INTEGRATION_PASS" if status == "PASS" else "S51_CLOSED_LOOP_INTEGRATION_FAIL")
    print({
        "release": "O45-S51",
        "status": status,
        "checks": checks,
        "path": "S46 governed execution -> S47 outcome -> S49 persisted trace -> S50 re-entry -> second governed cycle",
        "external_action_executed": False,
        "memory_write_executed": False,
        "internet_facing_production_approval": False,
        "notes": notes,
    })
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="")
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
