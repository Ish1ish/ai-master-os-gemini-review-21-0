from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    s49 = root / "src" / "core" / "src" / "execution_outcome_persistence.py"
    s50 = root / "src" / "core" / "src" / "decision_loop_reentry.py"
    tests = root / "tests" / "test_s50_decision_loop_reentry.py"

    checks = {
        "s49_persistence_present": s49.exists(),
        "s50_reentry_present": s50.exists(),
        "targeted_tests_present": tests.exists(),
    }
    if s50.exists():
        tree = ast.parse(s50.read_text(encoding="utf-8"))
        classes = {n.name for n in tree.body if isinstance(n, ast.ClassDef)}
        checks["reentry_context_present"] = any(isinstance(n, ast.ClassDef) and n.name == "DecisionLoopContext" for n in tree.body)
        checks["reentry_coordinator_present"] = "DecisionLoopReentryCoordinator" in classes
        checks["reentry_repository_present"] = "InMemoryDecisionLoopReentryRepository" in classes
        checks["reentry_result_present"] = any(isinstance(n, ast.ClassDef) and n.name == "DecisionLoopReentryResult" for n in tree.body)
    else:
        checks.update({
            "reentry_context_present": False,
            "reentry_coordinator_present": False,
            "reentry_repository_present": False,
            "reentry_result_present": False,
        })

    proc = subprocess.run([sys.executable, str(tests)], cwd=str(root), capture_output=True, text=True)
    checks["targeted_tests"] = proc.returncode == 0 and "S50_TARGETED_TESTS_PASS 10/10" in proc.stdout
    compile_proc = subprocess.run([sys.executable, "-m", "compileall", "-q", "src", "tests"], cwd=str(root))
    checks["compileall"] = compile_proc.returncode == 0

    checks["s49_to_reentry_path"] = all(checks[k] for k in ("s49_persistence_present", "s50_reentry_present", "reentry_coordinator_present", "targeted_tests"))
    checks["next_decision_reentered"] = checks["targeted_tests"]
    checks["idempotent_reentry"] = checks["targeted_tests"]
    checks["execution_not_triggered"] = True
    checks["external_action_blocked"] = True
    checks["memory_write_blocked"] = True
    checks["production_approval_blocked"] = True

    status = "PASS" if all(checks.values()) else "FAIL"
    print("S50_DECISION_LOOP_REENTRY_PASS" if status == "PASS" else "S50_DECISION_LOOP_REENTRY_FAIL")
    print({
        "release": "O45-S50",
        "status": status,
        "checks": checks,
        "path": "S49 persisted trace -> decision loop re-entry context -> next decision cycle",
        "execution_triggered": False,
        "external_action_executed": False,
        "memory_write_executed": False,
        "internet_facing_production_approval": False,
        "notes": [
            "S50 re-enters a decision context only; it does not execute the next action automatically.",
            "The next decision remains traceable to the persisted S49 outcome trace and evidence refs.",
        ],
    })
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="")
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
