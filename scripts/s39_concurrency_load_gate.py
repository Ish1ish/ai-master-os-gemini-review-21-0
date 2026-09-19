from __future__ import annotations
import json
import os
import sys
import importlib
import inspect

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src = os.path.join(ROOT, "src")
sys.path.insert(0, src)

checks = {}
notes = []

service_file = os.path.join(ROOT, "src", "core", "src", "service.py")
service_source = ""
if os.path.isfile(service_file):
    with open(service_file, "r", encoding="utf-8") as f:
        service_source = f.read()
checks["application_service_source_present"] = bool(service_source)
checks["application_service_class_present"] = "class ApplicationService" in service_source
checks["application_service_submit_present"] = "def submit(" in service_source
checks["application_service_execute_present"] = "def execute(" in service_source
if not all(checks[k] for k in ("application_service_source_present", "application_service_class_present", "application_service_submit_present", "application_service_execute_present")):
    notes.append("ApplicationService source contract missing")

runtime_file = os.path.join(ROOT, "src", "core", "src", "real_wiring.py")
runtime_source = ""
if os.path.isfile(runtime_file):
    with open(runtime_file, "r", encoding="utf-8") as f:
        runtime_source = f.read()
checks["o23_runtime_source_present"] = bool(runtime_source)
checks["o23_runtime_class_present"] = "class O23Runtime" in runtime_source
checks["o23_runtime_run_present"] = "def run(" in runtime_source
if not all(checks[k] for k in ("o23_runtime_source_present", "o23_runtime_class_present", "o23_runtime_run_present")):
    notes.append("O23Runtime source contract missing")

try:
    load_mod = importlib.import_module("core.src.runtime_load_validation")
    result = load_mod.run_controlled_load(count=24, concurrency=4)
    checks["concurrent_load_completed"] = result.completed == 24
    checks["no_load_failures"] = result.failed == 0
    checks["bounded_peak_inflight"] = result.peak_inflight <= 4
    checks["duplicate_active_run_blocked"] = result.duplicate_blocked
    checks["terminal_state_integrity"] = result.terminal_integrity
    load_metrics = {
        "submitted": result.submitted,
        "completed": result.completed,
        "failed": result.failed,
        "peak_inflight": result.peak_inflight,
        "duplicate_blocked": result.duplicate_blocked,
        "terminal_integrity": result.terminal_integrity,
        "elapsed_s": round(result.elapsed_s, 4),
    }
except Exception as exc:
    load_metrics = {"error": type(exc).__name__ + ": " + str(exc)[:240]}
    for k in ("concurrent_load_completed", "no_load_failures", "bounded_peak_inflight", "duplicate_active_run_blocked", "terminal_state_integrity"):
        checks[k] = False

try:
    import subprocess
    p = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tests", "test_s39_concurrency_load.py")],
        cwd=ROOT, text=True, capture_output=True, timeout=45,
    )
    checks["targeted_tests"] = p.returncode == 0 and "S39_TARGETED_TESTS_PASS 6/6" in p.stdout
    test_output = (p.stdout + p.stderr).strip()
except Exception as exc:
    checks["targeted_tests"] = False
    test_output = type(exc).__name__ + ": " + str(exc)

status = "PASS" if checks and all(checks.values()) else "FAIL"
report = {
    "release": "O39-S39",
    "status": status,
    "checks": checks,
    "load_metrics": load_metrics,
    "targeted_test_output": test_output,
    "external_action_executed": False,
    "memory_write_executed": False,
    "internet_facing_production_approval": False,
    "notes": notes,
}
os.makedirs(os.path.join(ROOT, "staging"), exist_ok=True)
with open(os.path.join(ROOT, "staging", "s39_concurrency_load.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
print("S39_CONCURRENCY_LOAD_" + status)
print(json.dumps(report, indent=2))
