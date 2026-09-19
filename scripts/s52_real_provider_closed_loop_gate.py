from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path


def _trace_by_id(snapshot, trace_id):
    if not isinstance(snapshot, dict):
        return None
    direct = snapshot.get(trace_id)
    if direct is not None:
        return direct
    for value in snapshot.values():
        if getattr(value, "trace_id", None) == trace_id:
            return value
        if isinstance(value, dict) and value.get("trace_id") == trace_id:
            return value
    return None


def _evidence_refs(trace):
    refs = getattr(trace, "evidence_refs", None)
    if refs is None and isinstance(trace, dict):
        refs = trace.get("evidence_refs", [])
    return refs or []


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    source = root / "src" / "core" / "src" / "real_provider_closed_loop.py"
    tests = root / "tests" / "test_s52_real_provider_closed_loop.py"
    s51 = root / "src" / "core" / "src" / "closed_loop_integration.py"
    checks = {
        "s51_present": s51.exists(),
        "s52_integration_present": source.exists(),
        "targeted_tests_present": tests.exists(),
        "real_provider_adapter_present": False,
        "real_provider_configuration": False,
        "provider_model_live": False,
        "provider_search_live": False,
        "provider_evidence_traceable": False,
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
            names = {n.name for n in tree.body if isinstance(n, ast.ClassDef)}
            checks["s52_integration_present"] = "RealProviderClosedLoopCoordinator" in names
        try:
            from core.src.live_providers import model_provider, provider_configuration_status, search_provider
            checks["real_provider_adapter_present"] = True
            cfg = provider_configuration_status()
            checks["real_provider_configuration"] = cfg.get("status") == "CONFIGURED"
        except Exception as exc:
            notes.append(f"provider_import_error={type(exc).__name__}")

        proc = subprocess.run([sys.executable, str(tests)], cwd=str(root), capture_output=True, text=True)
        checks["targeted_tests"] = proc.returncode == 0 and "S52_TARGETED_TESTS_PASS 10/10" in proc.stdout
        comp = subprocess.run([sys.executable, "-m", "compileall", "-q", "src", "tests"], cwd=str(root), capture_output=True, text=True)
        checks["compileall"] = comp.returncode == 0

        if not checks["real_provider_configuration"]:
            notes.append("real_provider_configuration_incomplete")
            raise RuntimeError("real_provider_configuration_incomplete")
        if not checks["targeted_tests"]:
            raise RuntimeError("targeted_tests_failed")

        from core.src.real_provider_closed_loop import RealProviderClosedLoopCoordinator
        coordinator = RealProviderClosedLoopCoordinator()
        result = coordinator.run_two_cycles(project_id="P-S52")
        checks["provider_model_live"] = bool(result.provider_evidence.model_hash)
        checks["provider_search_live"] = result.provider_evidence.search_result_count > 0 and bool(result.provider_evidence.search_hash)
        snapshot = coordinator.closed_loop.trace_snapshot()
        trace_objects = [_trace_by_id(snapshot, trace_id) for trace_id in result.closed_loop.trace_ids]
        checks["provider_evidence_traceable"] = all(
            trace is not None
            and any(ref.startswith("REAL-MODEL-") for ref in _evidence_refs(trace))
            and any(ref.startswith("REAL-SEARCH-") for ref in _evidence_refs(trace))
            for trace in trace_objects
        )
        checks["closed_loop_two_cycles"] = len(result.closed_loop.cycles) == 2 and all(c.execution_status == "EXECUTED" for c in result.closed_loop.cycles)
        checks["next_decision_reentered"] = all(c.reentry.next_decision == c.next_decision for c in result.closed_loop.cycles)
        checks["new_trace_each_cycle"] = result.closed_loop.trace_ids[0] != result.closed_loop.trace_ids[1]
        checks["external_action_blocked"] = result.external_action_executed is False
        checks["memory_write_blocked"] = result.memory_write_executed is False
        checks["execution_not_triggered_by_reentry"] = result.closed_loop.execution_triggered is False and all(not c.execution_triggered for c in result.closed_loop.cycles)
    except Exception as exc:
        notes.append(f"gate_runtime_error={type(exc).__name__}:{exc}")

    status = "PASS" if all(checks.values()) else "FAIL"
    print("S52_REAL_PROVIDER_CLOSED_LOOP_PASS" if status == "PASS" else "S52_REAL_PROVIDER_CLOSED_LOOP_FAIL")
    print(json.dumps({
        "release": "O45-S52.1",
        "status": status,
        "checks": checks,
        "path": "real provider evidence -> S51 closed loop cycle 1 -> persisted trace -> re-entry -> real provider refresh -> cycle 2",
        "external_action_executed": False,
        "memory_write_executed": False,
        "internet_facing_production_approval": False,
        "notes": notes,
    }, indent=2))
    if proc is not None and proc.stdout:
        print(proc.stdout, end="")
    if proc is not None and proc.stderr:
        print(proc.stderr, end="")
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
