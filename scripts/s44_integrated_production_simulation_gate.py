from __future__ import annotations
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from s44_integrated_simulation import run_deterministic_integration

r=run_deterministic_integration()
checks={
    "authenticated_request_path_present": r["application_service"],
    "governance_security_boundary_present": r["governance_boundary"] and r["security_integrity"],
    "real_provider_adapter_configured": r["provider_configured"] and r["provider_resilience"],
    "provider_failure_recovered": r["provider_recovery"],
    "runtime_bounded": r["runtime_bounded"],
    "crash_restart_reconciled": r["crash_reconciled"],
    "state_restore_integrity": r["restore_integrity"],
    "terminal_state_integrity": r["terminal_integrity"],
    "external_action_blocked": not r["external_action_executed"],
    "memory_write_blocked": not r["memory_write_executed"],
}
tests_ok=True
for name in ["test_s44_integrated_production_simulation.py"]:
    import subprocess
    cp=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/"tests"/name)],capture_output=True,text=True)
    tests_ok=tests_ok and cp.returncode==0
output={"release":"O39-S44","status":"PASS" if all(checks.values()) and tests_ok else "FAIL","checks":checks,"provider_status":r["provider_status"],"targeted_tests":tests_ok,"external_action_executed":r["external_action_executed"],"memory_write_executed":r["memory_write_executed"],"internet_facing_production_approval":False,"notes":[] if all(checks.values()) and tests_ok else [k for k,v in checks.items() if not v]}
print("S44_INTEGRATED_PRODUCTION_SIMULATION_"+output["status"])
print(json.dumps(output,indent=2))
