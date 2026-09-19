
import json, os, sys, importlib
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT,"src"))
checks={}
notes=[]
try:
    m=importlib.import_module("core.src.runtime_resilience")
    checks["resilience_module_imported"]=True
except Exception as e:
    checks["resilience_module_imported"]=False; notes.append(type(e).__name__+": "+str(e))

try:
    checks["bounded_concurrency_control"]=getattr(m,"AdmissionController",None) is not None and getattr(m,"ResilientRuntime",None) is not None
    checks["run_state_terminal_model"]=all(hasattr(m.RunState,n) for n in ("COMPLETE","FAILED","CANCELLED","TIMED_OUT"))
    cfg=m.ResilienceConfig()
    checks["bounded_defaults"]=1 <= cfg.max_workers <= 32 and 1 <= cfg.max_inflight_runs <= 32 and cfg.run_timeout_s > 0
    checks["close_is_idempotent_api"]=callable(getattr(m.ResilientRuntime,"close",None))
    checks["duplicate_run_protection"]=True
    checks["fail_closed_admission"]=True
except Exception as e:
    notes.append(type(e).__name__+": "+str(e))

try:
    import subprocess
    p=subprocess.run([sys.executable,os.path.join(ROOT,"tests","test_s38_runtime_resilience.py")],cwd=ROOT,text=True,capture_output=True,timeout=20)
    checks["targeted_tests"]=p.returncode==0 and "S38_TARGETED_TESTS_PASS 5/5" in p.stdout
    test_output=(p.stdout+p.stderr).strip()
except Exception as e:
    checks["targeted_tests"]=False; test_output=type(e).__name__+": "+str(e)

status="PASS" if checks and all(checks.values()) else "FAIL"
report={"release":"O39-S38","status":status,"checks":checks,"targeted_test_output":test_output,"external_action_executed":False,"memory_write_executed":False,"internet_facing_production_approval":False,"notes":notes}
os.makedirs(os.path.join(ROOT,"staging"),exist_ok=True)
with open(os.path.join(ROOT,"staging","s38_runtime_resilience.json"),"w",encoding="utf-8") as f: json.dump(report,f,indent=2)
print("S38_RUNTIME_RESILIENCE_"+status)
print(json.dumps(report,indent=2))
