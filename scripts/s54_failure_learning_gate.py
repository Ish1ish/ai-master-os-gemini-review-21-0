from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    source = root / "src" / "core" / "src" / "real_provider_failure_learning.py"
    tests = root / "tests" / "test_s54_failure_learning.py"
    s53 = root / "src" / "core" / "src" / "real_provider_failure_recovery.py"
    checks = {
        "s53_present": s53.exists(),
        "learning_module_present": source.exists(),
        "targeted_tests_present": tests.exists(),
        "learning_signal_present": False,
        "adaptive_recovery_decision_present": False,
        "traceable_evidence_present": False,
        "failure_recovery_learning_present": False,
        "next_decision_routing_present": False,
        "idempotent_learning_trace": False,
        "execution_not_triggered": False,
        "external_action_blocked": False,
        "memory_write_blocked": False,
        "targeted_tests": False,
        "compileall": False,
    }
    notes: list[str] = []
    proc = None
    try:
        if source.exists():
            tree = ast.parse(source.read_text(encoding="utf-8"))
            classes = {n.name for n in tree.body if isinstance(n, ast.ClassDef)}
            checks["learning_signal_present"] = "FailureLearningSignal" in classes
            checks["adaptive_recovery_decision_present"] = "AdaptiveRecoveryDecision" in classes
            checks["traceable_evidence_present"] = "evidence_refs" in source.read_text(encoding="utf-8")
            checks["next_decision_routing_present"] = "next_decision" in source.read_text(encoding="utf-8")
            checks["failure_recovery_learning_present"] = "TRANSIENT_PROVIDER_FAILURE" in source.read_text(encoding="utf-8")
            checks["idempotent_learning_trace"] = "idempotent_replay" in source.read_text(encoding="utf-8")
            checks["execution_not_triggered"] = "execution_triggered=False" in source.read_text(encoding="utf-8")
            checks["external_action_blocked"] = "external_action_executed=False" in source.read_text(encoding="utf-8")
            checks["memory_write_blocked"] = "memory_write_executed=False" in source.read_text(encoding="utf-8")

        proc = subprocess.run([sys.executable, str(tests)], cwd=str(root), capture_output=True, text=True)
        checks["targeted_tests"] = proc.returncode == 0 and "S54_TARGETED_TESTS_PASS 12/12" in proc.stdout
        comp = subprocess.run([sys.executable, "-m", "compileall", "-q", "src", "tests"], cwd=str(root), capture_output=True, text=True)
        checks["compileall"] = comp.returncode == 0
        if not checks["targeted_tests"]:
            raise RuntimeError("targeted_tests_failed")

        from core.src.real_provider_failure_learning import FailureLearningCoordinator, FailureLearningRepository

        class Recovery:
            injected_model_failures = 1
            injected_search_failures = 1
            model_attempts = 3
            search_attempts = 3

        repo = FailureLearningRepository()
        coordinator = FailureLearningCoordinator(repo)
        first = coordinator.observe(Recovery(), recovery_run_id="S54-REAL-PROVIDER-RECOVERY-001")
        second = coordinator.observe(Recovery(), recovery_run_id="S54-REAL-PROVIDER-RECOVERY-001")
        checks["failure_recovery_learning_present"] = first.learning_signal.failure_class == "TRANSIENT_PROVIDER_FAILURE"
        checks["traceable_evidence_present"] = bool(first.learning_signal.evidence_refs)
        checks["next_decision_routing_present"] = first.next_decision == "BOUNDED_NEXT_STEP"
        checks["idempotent_learning_trace"] = second.idempotent_replay is True and len(repo.snapshot()) == 1
        checks["execution_not_triggered"] = first.decision.execution_triggered is False
        checks["external_action_blocked"] = first.decision.external_action_executed is False
        checks["memory_write_blocked"] = first.decision.memory_write_executed is False
    except Exception as exc:
        notes.append(f"gate_runtime_error={type(exc).__name__}:{exc}")

    status = "PASS" if all(checks.values()) else "FAIL"
    print("S54_FAILURE_LEARNING_PASS" if status == "PASS" else "S54_FAILURE_LEARNING_FAIL")
    print(json.dumps({
        "release": "O45-S54",
        "status": status,
        "checks": checks,
        "path": "S53 provider failure/recovery -> learning signal -> adaptive next decision",
        "failure_learning_recorded": checks["failure_recovery_learning_present"],
        "next_decision": "BOUNDED_NEXT_STEP" if checks["next_decision_routing_present"] else None,
        "external_action_executed": False,
        "memory_write_executed": False,
        "execution_triggered": False,
        "internet_facing_production_approval": False,
        "notes": notes,
    }, indent=2))
    if proc and proc.stdout:
        print(proc.stdout, end="")
    if proc and proc.stderr:
        print(proc.stderr, end="")
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
