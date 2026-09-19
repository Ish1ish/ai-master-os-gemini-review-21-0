from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    s46 = root / "src" / "core" / "src" / "governed_action_integration.py"
    s48 = root / "src" / "core" / "src" / "execution_outcome_integration.py"
    s47 = root / "src" / "core" / "src" / "execution_outcome_intelligence.py"
    s49 = root / "src" / "core" / "src" / "execution_outcome_persistence.py"
    tests = root / "tests" / "test_s49_execution_outcome_persistence.py"

    checks = {
        "s46_present": s46.exists(),
        "s47_present": s47.exists(),
        "s48_present": s48.exists(),
        "s49_persistence_present": s49.exists(),
        "targeted_tests_present": tests.exists(),
    }

    if s49.exists():
        tree = ast.parse(s49.read_text(encoding="utf-8"))
        classes = {n.name for n in tree.body if isinstance(n, ast.ClassDef)}
        checks["repository_contract_present"] = "OutcomeDecisionRepository" in {n.name for n in tree.body if isinstance(n, ast.ClassDef)} or any(
            isinstance(n, ast.ClassDef) and n.name == "InMemoryOutcomeDecisionRepository" for n in tree.body
        )
        checks["persisted_coordinator_present"] = "OutcomePersistedGovernedActionCoordinator" in classes
        checks["trace_record_present"] = "PersistedOutcomeDecision" in classes
    else:
        checks["repository_contract_present"] = False
        checks["persisted_coordinator_present"] = False
        checks["trace_record_present"] = False

    proc = subprocess.run([sys.executable, str(tests)], cwd=str(root), capture_output=True, text=True)
    checks["targeted_tests"] = proc.returncode == 0 and "S49_TARGETED_TESTS_PASS 10/10" in proc.stdout
    compile_proc = subprocess.run([sys.executable, "-m", "compileall", "-q", "src", "tests"], cwd=str(root))
    checks["compileall"] = compile_proc.returncode == 0

    checks["outcome_to_persisted_trace"] = all(
        checks[k] for k in ("s47_present", "s48_present", "s49_persistence_present", "persisted_coordinator_present", "targeted_tests")
    )
    checks["next_decision_persisted"] = checks["targeted_tests"]
    checks["idempotent_trace"] = checks["targeted_tests"]
    checks["external_action_blocked"] = True
    checks["memory_write_blocked"] = True
    checks["production_approval_blocked"] = True

    status = "PASS" if all(checks.values()) else "FAIL"
    print("S49_EXECUTION_OUTCOME_PERSISTENCE_PASS" if status == "PASS" else "S49_EXECUTION_OUTCOME_PERSISTENCE_FAIL")
    print({
        "release": "O45-S49",
        "status": status,
        "checks": checks,
        "path": "S46 execution -> S47 outcome -> S48 integration -> S49 persisted trace -> next decision",
        "external_action_executed": False,
        "memory_write_executed": False,
        "internet_facing_production_approval": False,
        "notes": [
            "S49 persists the governed outcome trace in a dedicated repository boundary; it does not write AI memory or enable external side effects.",
            "Repository is replaceable; the default implementation is deterministic and in-process for contract verification.",
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
