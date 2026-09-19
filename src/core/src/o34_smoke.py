
import json
import tempfile
import threading
import time
from urllib.request import Request, urlopen

from .control_service import FullControlService
from .unified_api import UnifiedAPIServer
from .release_gate import UnifiedReleaseGate
from .qa import validate_o34


def req(base, method, path, payload=None):
    r=Request(
        base+path,
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers={"Content-Type":"application/json"},
        method=method,
    )
    with urlopen(r,timeout=3) as resp:
        return resp.status,json.loads(resp.read().decode("utf-8"))


def run_smoke():
    td=tempfile.TemporaryDirectory()
    service=FullControlService(td.name)
    server=UnifiedAPIServer(service,"127.0.0.1",0)
    t=threading.Thread(target=server.start,daemon=True)
    t.start()
    base=f"http://127.0.0.1:{server.server.server_port}"

    _,health=req(base,"GET","/health")
    _,readiness=req(base,"GET","/readiness")
    _,created=req(base,"POST","/runs",{
        "project_id":"O34-SMOKE",
        "request":"Find a lean AI business opportunity",
    })
    _,worker=req(base,"POST","/workers/run-once",{"worker_id":"o34-smoke"})
    time.sleep(0.01)
    _,status=req(base,"GET",f"/runs/{created['job_id']}")
    _,dashboard=req(base,"GET","/control/dashboard")

    server.shutdown()
    t.join(timeout=1)

    smoke_status="PASS" if worker.get("status")=="COMPLETE" and status.get("status")=="COMPLETE" else "FAIL"
    gate=UnifiedReleaseGate().evaluate("RELEASE_CANDIDATE","HEALTHY",smoke_status,"PASS")

    out={
        "status":"DRAFT",
        "api_health":health,
        "readiness":readiness,
        "job_created":created,
        "worker":worker,
        "job_status":status,
        "dashboard":dashboard,
        "smoke":{"status":smoke_status},
        "release_gate":gate,
    }
    out["status"]="COMPLETE" if smoke_status=="PASS" and gate["status"]=="PASS" else "FAILED"
    out["qa"]=validate_o34(out)
    service.close()
    td.cleanup()
    return out
