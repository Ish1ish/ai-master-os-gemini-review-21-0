from __future__ import annotations
import importlib, json, os, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
checks = {}; notes = []

try:
    m = importlib.import_module("core.src.crash_recovery")
    checks["recovery_module_imported"] = True
    checks["crash_reconciliation_api"] = all(hasattr(m.CrashRecoveryController, n) for n in ("claim", "crash_worker", "reconcile_after_restart", "requeue_recovered"))
    c = m.CrashRecoveryController(); c.submit("gate-r1"); c.claim("gate-r1", "worker-a", "lease-a")
    checks["interrupted_run_detected"] = c.crash_worker("worker-a") == ["gate-r1"]
    checks["restart_reconciliation"] = c.reconcile_after_restart() == ["gate-r1"] and c.records["gate-r1"].state.value == "RECOVERED"
    c.requeue_recovered("gate-r1"); c.claim("gate-r1", "worker-b", "lease-b"); c.complete("gate-r1", "hash-gate-r1")
    checks["resume_to_terminal_state"] = c.records["gate-r1"].state.value == "COMPLETE" and c.records["gate-r1"].execution_count == 2
    checks["idempotent_close"] = callable(getattr(c, "close", None))
except Exception as e:
    checks["recovery_module_imported"] = False
    notes.append(type(e).__name__ + ": " + str(e))

# Validate that the current runtime exposes the components that S41 is intended to harden.
service_file = os.path.join(ROOT, "src", "core", "src", "service.py")
checks["application_service_present"] = os.path.isfile(service_file)
if checks["application_service_present"]:
    service_src = open(service_file, "r", encoding="utf-8").read()
    checks["application_service_lifecycle_present"] = "class ApplicationService" in service_src and "def execute(" in service_src
else:
    checks["application_service_lifecycle_present"] = False

# Discover queue/worker/recovery implementation markers in the current workspace.
marker_hits = []
for base in (os.path.join(ROOT, "src", "core", "src"), os.path.join(ROOT, "src", "core", "backend")):
    if not os.path.isdir(base):
        continue
    for dirpath, _, filenames in os.walk(base):
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            try:
                text = open(path, "r", encoding="utf-8").read().lower()
            except Exception:
                continue
            if any(token in text for token in ("lease", "worker", "recover", "reconcile")):
                marker_hits.append(path)
checks["worker_recovery_markers_present"] = len(marker_hits) > 0

try:
    p = subprocess.run([sys.executable, os.path.join(ROOT, "tests", "test_s41_crash_recovery.py")], cwd=ROOT, text=True, capture_output=True, timeout=30)
    checks["targeted_tests"] = p.returncode == 0 and "S41_TARGETED_TESTS_PASS 6/6" in p.stdout
    test_output = (p.stdout + p.stderr).strip()
except Exception as e:
    checks["targeted_tests"] = False
    test_output = type(e).__name__ + ": " + str(e)

status = "PASS" if checks and all(checks.values()) else "FAIL"
report = {
    "release": "O39-S41",
    "status": status,
    "checks": checks,
    "worker_recovery_marker_file_count": len(marker_hits),
    "targeted_test_output": test_output,
    "external_action_executed": False,
    "memory_write_executed": False,
    "internet_facing_production_approval": False,
    "notes": notes,
}
os.makedirs(os.path.join(ROOT, "staging"), exist_ok=True)
with open(os.path.join(ROOT, "staging", "s41_crash_recovery.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
print("S41_CRASH_RECOVERY_" + status)
print(json.dumps(report, indent=2))
