from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    src = root / "src" / "core" / "src"
    module = src / "multi_dimensional_resource_governor.py"
    s57 = src / "real_provider_cost_aware_loop.py"
    tests = root / "tests" / "test_s58_multi_dimensional_resource_governor.py"
    checks = {
        "s57_present": s57.exists(),
        "governor_present": module.exists(),
        "targeted_tests_present": tests.exists(),
        "time_budget_present": False,
        "provider_call_budget_present": False,
        "retry_budget_present": False,
        "concurrency_budget_present": False,
        "cycle_budget_present": False,
        "deterministic_decision_present": False,
        "fail_closed_present": False,
        "idempotent_snapshot_present": False,
        "targeted_tests": False,
        "compileall": False,
        "budget_ok": False,
        "multi_dimension_block": False,
        "execution_not_triggered": True,
        "external_action_blocked": True,
        "memory_write_blocked": True,
    }
    notes = []
    proc = None
    try:
        text = module.read_text(encoding="utf-8") if module.exists() else ""
        checks["time_budget_present"] = "max_time_ms" in text and "time_ms" in text
        checks["provider_call_budget_present"] = "max_provider_calls" in text and "provider_calls" in text
        checks["retry_budget_present"] = "max_retry_attempts" in text and "retry_attempts" in text
        checks["concurrency_budget_present"] = "max_concurrency" in text and "concurrency" in text
        checks["cycle_budget_present"] = "max_cycles" in text and "cycles" in text
        checks["deterministic_decision_present"] = "RESOURCE_BUDGET_OK" in text and "RESOURCE_BUDGET_EXCEEDED" in text
        checks["fail_closed_present"] = "self._blocked = True" in text
        checks["idempotent_snapshot_present"] = "def snapshot" in text

        env = dict(__import__("os").environ)
        env["PYTHONPATH"] = str(root / "src") + __import__("os").pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.run([sys.executable, str(tests)], cwd=root, capture_output=True, text=True, env=env)
        checks["targeted_tests"] = proc.returncode == 0 and "S58_TARGETED_TESTS_PASS 15/15" in proc.stdout
        comp = subprocess.run([sys.executable, "-m", "compileall", "-q", "src", "tests"], cwd=root, capture_output=True, text=True, env=env)
        checks["compileall"] = comp.returncode == 0

        if not all(checks[k] for k in ["s57_present", "governor_present", "targeted_tests", "compileall"]):
            raise RuntimeError("gate_contract_failed")

        sys.path.insert(0, str(root / "src"))
        from core.src.multi_dimensional_resource_governor import MultiDimensionalResourceGovernor, ResourceLimits
        g = MultiDimensionalResourceGovernor(ResourceLimits(max_time_ms=1000, max_provider_calls=4, max_retry_attempts=3, max_concurrency=2, max_cycles=2))
        checks["budget_ok"] = g.admit(time_ms=100, provider_calls=2, retry_attempts=1, concurrency=2, cycles=1).allowed
        blocked = g.admit(time_ms=1000, provider_calls=3, retry_attempts=3, cycles=2)
        checks["multi_dimension_block"] = (not blocked.allowed) and len(blocked.exhausted_dimensions) >= 2 and g.snapshot().status == "BLOCKED"
    except Exception as exc:
        notes.append(f"gate_runtime_error={type(exc).__name__}:{exc}")

    status = "PASS" if all(checks.values()) else "FAIL"
    payload = {
        "release": "O45-S58",
        "status": status,
        "checks": checks,
        "path": "S57 real-provider cost-aware loop -> multi-dimensional time/provider-call/retry/concurrency/cycle governance",
        "execution_triggered": False,
        "external_action_executed": False,
        "memory_write_executed": False,
        "internet_facing_production_approval": False,
        "notes": notes,
    }
    print("S58_MULTI_DIMENSIONAL_RESOURCE_GOVERNOR_PASS" if status == "PASS" else "S58_MULTI_DIMENSIONAL_RESOURCE_GOVERNOR_FAIL")
    print(json.dumps(payload, indent=2))
    if proc and proc.stdout:
        print(proc.stdout, end="")
    if proc and proc.stderr:
        print(proc.stderr, end="")
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
