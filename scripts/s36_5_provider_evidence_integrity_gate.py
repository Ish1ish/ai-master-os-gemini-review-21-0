import hashlib, json, os, tempfile
from pathlib import Path
from unittest.mock import patch

def sha256(p):
    h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()

def main():
    os.environ["AI_OS_ENV"]="production"
    repo=Path(__file__).resolve().parents[1]
    service_path=repo/"src/core/src/service.py"
    wiring_path=repo/"src/core/src/real_wiring.py"
    live_path=repo/"src/core/src/live_providers.py"
    out=repo/"staging/s36_5_provider_evidence_integrity.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    r={"release":"O39-S36.5","status":"FAIL","checks":{
        "service_source_hash":sha256(service_path) if service_path.exists() else None,
        "wiring_source_hash":sha256(wiring_path) if wiring_path.exists() else None,
        "live_provider_source_hash":sha256(live_path) if live_path.exists() else None,
        "production_branch_static":False,"live_provider_import_static":False,
        "live_model_called":False,"live_search_called":False,
        "fake_model_called":False,"fake_search_called":False,
        "execute_status":None,"run_completed":False,
        "provider_evidence_present":False,"external_action_executed":False,
        "memory_write_executed":False,
        "provider_evidence_valid":False,
    },"result":{},"notes":[]}
    try:
        s=service_path.read_text(encoding="utf-8")
        w=wiring_path.read_text(encoding="utf-8")
        r["checks"]["production_branch_static"]=(
            'AI_OS_ENV' in s and 'in {"prod", "production"}' in s and
            'model_provider=model_provider' in s and
            'search_provider=search_provider' in s)
        r["checks"]["live_provider_import_static"] = (
            'from .live_providers import model_provider, search_provider, provider_configuration_status' in s)
        import core.src.live_providers as lp
        real_model, real_search = lp.model_provider, lp.search_provider
        from core.src import providers as fp
        fake_model, fake_search = fp.fake_model_provider, fp.fake_search_provider
        calls={"model":0,"search":0,"fake_model":0,"fake_search":0}
        def wrapped_model(prompt):
            calls["model"]+=1
            return real_model(prompt)
        def wrapped_search(query):
            calls["search"]+=1
            return real_search(query)
        def blocked_fake_model(*a,**k):
            calls["fake_model"]+=1
            raise AssertionError("fake_model_provider_used_in_production")
        def blocked_fake_search(*a,**k):
            calls["fake_search"]+=1
            raise AssertionError("fake_search_provider_used_in_production")
        # Re-import ApplicationService after replacing the provider functions it imports.
        import sys
        sys.modules.pop("core.src.service", None)
        with patch.object(lp,"model_provider",wrapped_model), patch.object(lp,"search_provider",wrapped_search), \
             patch.object(fp,"fake_model_provider",blocked_fake_model), patch.object(fp,"fake_search_provider",blocked_fake_search):
            from core.src.service import ApplicationService
            with tempfile.TemporaryDirectory(prefix="aios_s36_5_") as td:
                svc=ApplicationService(db_path=str(Path(td)/"jobs.sqlite3"))
                sub=svc.submit("S36-5-STAGING",
                    "Perform a controlled staging validation using live research and a live model. Return a compact structured result. No consequential action.",
                    audience="small businesses validating AI workflows",
                    goal="provider evidence integrity validation",
                    constraints=["staging-only","no spending","no messaging","no publishing"],
                    internal=True)
                job=sub.get("job_id")
                if job:
                    res=svc.execute(job,internal=True)
                    r["checks"]["execute_status"]=res.get("status")
                    r["checks"]["run_completed"]=res.get("status")=="COMPLETE"
                    r["result"]={"status":res.get("status"),"error":res.get("error"),
                                 "failed_stage":res.get("failed_stage"),
                                 "runtime_status":res.get("runtime_status"),
                                 "result_keys":sorted(res.get("result",{}).keys()) if isinstance(res.get("result"),dict) else []}
                    r["checks"]["external_action_executed"]=bool(res.get("result",{}).get("external_action_executed",False)) if isinstance(res.get("result"),dict) else False
                    r["checks"]["memory_write_executed"]=bool(res.get("result",{}).get("memory_write_executed",False)) if isinstance(res.get("result"),dict) else False
                    rr=res.get("result",{}) if isinstance(res,dict) else {}
                    txt=json.dumps(rr,ensure_ascii=False).lower()
                    evidence_keys=[k for k in ("provider","model","text","results","raw_output_hash","latency_ms") if k in txt]
                    r["checks"]["provider_evidence_present"]=len(evidence_keys)>=2 or calls["model"]>0 or calls["search"]>0
                    r["checks"]["provider_evidence_valid"]=calls["model"]>0 and calls["search"]>0 and r["checks"]["run_completed"]
                svc.close()
        r["checks"]["live_model_called"]=calls["model"]>0
        r["checks"]["live_search_called"]=calls["search"]>0
        r["checks"]["fake_model_called"]=calls["fake_model"]>0
        r["checks"]["fake_search_called"]=calls["fake_search"]>0
        strict=(r["checks"]["production_branch_static"] and r["checks"]["live_provider_import_static"] and
                r["checks"]["live_model_called"] and r["checks"]["live_search_called"] and
                not r["checks"]["fake_model_called"] and not r["checks"]["fake_search_called"] and
                r["checks"]["execute_status"]=="COMPLETE" and r["checks"]["provider_evidence_valid"] and
                not r["checks"]["external_action_executed"] and not r["checks"]["memory_write_executed"])
        r["status"]="PASS" if strict else "FAIL"
    except Exception as e:
        r["notes"].append("gate_exception")
        r["result"]={"type":type(e).__name__,"message":str(e)}
    out.write_text(json.dumps(r,indent=2),encoding="utf-8")
    print("S36_5_PROVIDER_EVIDENCE_INTEGRITY_"+r["status"])
    return 0 if r["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
