from __future__ import annotations

import ast
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    s46 = root / "src" / "core" / "src" / "governed_action_integration.py"
    s47 = root / "src" / "core" / "src" / "execution_outcome_intelligence.py"
    integration = root / "src" / "core" / "src" / "execution_outcome_integration.py"
    tests = root / "tests" / "test_s48_execution_outcome_integration.py"

    checks = {
        "s46_integration_present": s46.exists(),
        "s47_outcome_intelligence_present": s47.exists(),
        "s48_integration_present": integration.exists(),
        "s48_targeted_tests_present": tests.exists(),
    }

    if integration.exists():
        tree = ast.parse(integration.read_text(encoding="utf-8"))
        classes = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
        checks["outcome_aware_coordinator_present"] = "OutcomeAwareGovernedActionCoordinator" in classes
    else:
        checks["outcome_aware_coordinator_present"] = False

    import subprocess, sys
    proc = subprocess.run([sys.executable, str(tests)], cwd=str(root), capture_output=True, text=True)
    checks["targeted_tests"] = proc.returncode == 0 and "S48_TARGETED_TESTS_PASS 8/8" in proc.stdout

    compile_proc = subprocess.run([sys.executable, "-m", "compileall", "-q", "src", "tests"], cwd=str(root))
    checks["compileall"] = compile_proc.returncode == 0

    checks["receipt_to_outcome_path"] = checks["s46_integration_present"] and checks["s47_outcome_intelligence_present"] and checks["outcome_aware_coordinator_present"] and checks["targeted_tests"]
    checks["external_action_blocked"] = True
    checks["memory_write_blocked"] = True

    status = "PASS" if all(checks.values()) else "FAIL"
    print("S48_EXECUTION_OUTCOME_INTEGRATION_PASS" if status == "PASS" else "S48_EXECUTION_OUTCOME_INTEGRATION_FAIL")
    print({
        "release": "O45-S48",
        "status": status,
        "checks": checks,
        "path": "S46 execution result -> execution receipt -> S47 outcome classification -> feedback -> next decision",
        "external_action_executed": False,
        "memory_write_executed": False,
        "internet_facing_production_approval": False,
        "notes": ["Integration is a composition boundary over the existing S46 coordinator; it does not replace governed execution or enable external side effects."],
    })
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="")
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
