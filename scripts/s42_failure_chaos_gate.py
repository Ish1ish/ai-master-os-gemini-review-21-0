from __future__ import annotations
import importlib, json, os, subprocess, sys, traceback

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
checks = {}
notes = []

modules = {}
for name in ("core.src.provider_resilience", "core.src.runtime_resilience", "core.src.crash_recovery", "core.src.chaos_drill"):
    try:
        modules[name] = importlib.import_module(name)
    except Exception as exc:
        notes.append(f"{name}:{type(exc).__name__}:{exc}")

checks["provider_reliability_present"] = "core.src.provider_resilience" in modules
checks["runtime_resilience_present"] = "core.src.runtime_resilience" in modules
checks["crash_recovery_present"] = "core.src.crash_recovery" in modules
checks["chaos_drill_present"] = "core.src.chaos_drill" in modules

service_file = os.path.join(ROOT, "src", "core", "src", "service.py")
checks["application_service_present"] = os.path.isfile(service_file)
if checks["application_service_present"]:
    src = open(service_file, "r", encoding="utf-8").read()
    checks["application_service_lifecycle_present"] = "class ApplicationService" in src and "def execute(" in src
else:
    checks["application_service_lifecycle_present"] = False

try:
    result = modules["core.src.chaos_drill"].run_combined_chaos()
    for key in (
        "model_recovered_after_5xx",
        "search_recovered_after_429",
        "runtime_bounded_peak",
        "runtime_terminal_integrity",
        "runtime_failure_contained",
        "recovery_detected_interruption",
        "recovery_reconciled_after_restart",
        "recovery_terminal_after_resume",
        "duplicate_lease_blocked",
        "provider_snapshot_safe",
    ):
        checks[key] = bool(result.get(key))
    chaos_result = result
except Exception as exc:
    checks["chaos_execution"] = False
    notes.append(traceback.format_exc(limit=3))
    chaos_result = {}

try:
    p = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tests", "test_s42_failure_chaos.py")],
        cwd=ROOT, text=True, capture_output=True, timeout=30
    )
    checks["targeted_tests"] = p.returncode == 0 and "S42_TARGETED_TESTS_PASS 8/8" in p.stdout
    test_output = (p.stdout + p.stderr).strip()
except Exception as exc:
    checks["targeted_tests"] = False
    test_output = f"{type(exc).__name__}: {exc}"

status = "PASS" if checks and all(checks.values()) else "FAIL"
report = {
    "release": "O39-S42",
    "status": status,
    "checks": checks,
    "chaos_metrics": {
        "admission_failures": chaos_result.get("admission_failures"),
        "peak_inflight": chaos_result.get("peak_inflight"),
        "model_attempts": chaos_result.get("model_attempts"),
        "search_attempts": chaos_result.get("search_attempts"),
        "runtime_results": chaos_result.get("runtime_results"),
    },
    "targeted_test_output": test_output,
    "external_action_executed": False,
    "memory_write_executed": False,
    "internet_facing_production_approval": False,
    "notes": notes,
}
os.makedirs(os.path.join(ROOT, "staging"), exist_ok=True)
with open(os.path.join(ROOT, "staging", "s42_failure_chaos.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
print("S42_FAILURE_CHAOS_" + status)
print(json.dumps(report, indent=2))
