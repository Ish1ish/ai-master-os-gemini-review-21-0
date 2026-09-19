from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    source = root / "src" / "core" / "src" / "real_provider_failure_recovery.py"
    tests = root / "tests" / "test_s53_real_provider_failure_recovery.py"
    s52 = root / "src" / "core" / "src" / "real_provider_closed_loop.py"
    s51 = root / "src" / "core" / "src" / "closed_loop_integration.py"
    checks = {
        "s51_present": s51.exists(),
        "s52_present": s52.exists(),
        "s53_recovery_present": source.exists(),
        "targeted_tests_present": tests.exists(),
        "failure_injection_present": False,
        "bounded_recovery_present": False,
        "real_provider_configuration": False,
        "provider_model_live": False,
        "provider_search_live": False,
        "transient_failure_recovered": False,
        "persistent_failure_fail_closed": False,
        "closed_loop_two_cycles": False,
        "next_decision_reentered": False,
        "new_trace_each_cycle": False,
        "external_action_blocked": False,
        "memory_write_blocked": False,
        "execution_not_triggered_by_reentry": False,
        "targeted_tests": False,
        "compileall": False,
    }
    notes = []
    proc = None
    try:
        if source.exists():
            tree = ast.parse(source.read_text(encoding="utf-8"))
            classes = {n.name for n in tree.body if isinstance(n, ast.ClassDef)}
            checks["failure_injection_present"] = "TransientFailureInjector" in classes
            checks["bounded_recovery_present"] = "BoundedProviderRecovery" in classes

        proc = subprocess.run([sys.executable, str(tests)], cwd=str(root), capture_output=True, text=True)
        checks["targeted_tests"] = proc.returncode == 0 and "S53_TARGETED_TESTS_PASS 12/12" in proc.stdout
        comp = subprocess.run([sys.executable, "-m", "compileall", "-q", "src", "tests"], cwd=str(root), capture_output=True, text=True)
        checks["compileall"] = comp.returncode == 0

        from core.src.live_providers import model_provider, provider_configuration_status, search_provider
        cfg = provider_configuration_status()
        checks["real_provider_configuration"] = cfg.get("status") == "CONFIGURED"
        if not checks["real_provider_configuration"]:
            notes.append("real_provider_configuration_incomplete")
            raise RuntimeError("real_provider_configuration_incomplete")
        if not checks["targeted_tests"]:
            raise RuntimeError("targeted_tests_failed")

        from core.src.real_provider_failure_recovery import RealProviderFailureRecoveryCoordinator

        coordinator = RealProviderFailureRecoveryCoordinator(
            model=model_provider,
            search=search_provider,
            model_failures=1,
            search_failures=1,
            max_attempts=2,
            allow_external_execution=False,
        )
        result = coordinator.run(project_id="P-S53")
        checks["transient_failure_recovered"] = (
            result.injected_model_failures == 1
            and result.injected_search_failures == 1
            and result.model_attempts == 3
            and result.search_attempts == 3
        )
        checks["provider_model_live"] = result.model_attempts >= 3 and all(c.execution_status == "EXECUTED" for c in result.closed_loop.closed_loop.cycles)
        checks["provider_search_live"] = result.search_attempts >= 3 and result.injected_search_failures == 1
        trace_map = coordinator.coordinator.closed_loop.trace_snapshot()
        checks["closed_loop_two_cycles"] = len(result.closed_loop.closed_loop.cycles) == 2
        checks["next_decision_reentered"] = all(c.reentry.next_decision == c.next_decision for c in result.closed_loop.closed_loop.cycles)
        checks["new_trace_each_cycle"] = result.closed_loop.closed_loop.trace_ids[0] != result.closed_loop.closed_loop.trace_ids[1]
        checks["provider_model_live"] = checks["provider_model_live"] and bool(trace_map)
        checks["transient_failure_recovered"] = checks["transient_failure_recovered"] and bool(trace_map)
        checks["external_action_blocked"] = result.external_action_executed is False
        checks["memory_write_blocked"] = result.memory_write_executed is False
        checks["execution_not_triggered_by_reentry"] = (
            result.closed_loop.closed_loop.execution_triggered is False
            and all(c.execution_triggered is False for c in result.closed_loop.closed_loop.cycles)
        )

        def persistent_failure(_prompt):
            raise RuntimeError("persistent_provider_failure")

        failing = RealProviderFailureRecoveryCoordinator(
            model=persistent_failure,
            search=search_provider,
            model_failures=0,
            search_failures=0,
            max_attempts=2,
            allow_external_execution=False,
        )
        try:
            failing.run(project_id="P-S53-PERSISTENT-FAIL")
        except RuntimeError as exc:
            checks["persistent_failure_fail_closed"] = "recovery_exhausted" in str(exc)
        else:
            checks["persistent_failure_fail_closed"] = False

    except Exception as exc:
        notes.append(f"gate_runtime_error={type(exc).__name__}:{exc}")

    status = "PASS" if all(checks.values()) else "FAIL"
    print("S53_REAL_PROVIDER_FAILURE_RECOVERY_PASS" if status == "PASS" else "S53_REAL_PROVIDER_FAILURE_RECOVERY_FAIL")
    print(json.dumps({
        "release": "O45-S53",
        "status": status,
        "checks": checks,
        "path": "real provider -> injected transient failure -> bounded recovery -> S52/S51 closed loop -> persisted trace -> re-entry -> second cycle",
        "external_action_executed": False,
        "memory_write_executed": False,
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
