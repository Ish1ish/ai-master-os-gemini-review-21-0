import json
import os
import tempfile
import threading
import urllib.request
import unittest

from src.api import InProcessAPI
from src.http_server import O32HTTPServer
from src.service import ApplicationService


class FakeRuntime:
    def run(self, run_id, project_id, request, audience=None, goal=None, constraints=None, language="en"):
        return {"status":"COMPLETE","run_id":run_id,"project_id":project_id,"decision_surface":{
            "recommendation":"Workflow automation","customer":audience,"problem":"Repeated manual work","desired_outcome":"Reduce work","opportunity_score":6,"strategy_score":7.7,"confidence":"medium","evidence_boundary":"local_evidence_supported",
            "validation_experiment":{"experiment_id":f"VAL-{run_id}","hypothesis":"Problem is material","sample_size":10,"method":"Interview 10","success_threshold":{"problem_confirmation":"At least 6/10","high_intent":"At least 3/10"},"decision_rule":"GO when met; otherwise refine.","external_action_required":False}}}
    def close(self): pass


class TestO42HTTPAPI(unittest.TestCase):
    def test_experiment_http_surface_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            service=ApplicationService(db_path=os.path.join(td,"jobs.sqlite3"),runtime=FakeRuntime())
            api=InProcessAPI(service)
            server=O32HTTPServer(api,host="127.0.0.1",port=0,require_auth=False)
            thread=threading.Thread(target=server.start,daemon=True); thread.start()
            host,port=server.server.server_address
            base=f"http://{host}:{port}"
            def req(path, method="GET", payload=None):
                body=None; headers={}
                if payload is not None:
                    body=json.dumps(payload).encode(); headers["Content-Type"]="application/json"
                r=urllib.request.urlopen(urllib.request.Request(base+path,data=body,headers=headers,method=method),timeout=5)
                return json.loads(r.read().decode())
            try:
                created=req("/runs","POST",{"project_id":"PROJ","request":"validate","audience":"SMEs","goal":"validate"})
                run_id=created["job_id"]
                req(f"/runs/{run_id}/execute","POST",{})
                exp=req("/experiments/from-run","POST",{"run_id":run_id})
                self.assertEqual(exp["status"],"READY")
                saved=req(f"/experiments/{exp['experiment_id']}/evidence","POST",{"sample_size":10,"metrics":{"problem_confirmation":7,"high_intent":4},"evidence_refs":["E1","E2"]})
                self.assertEqual(saved["status"],"EVIDENCE_RECORDED")
                evaluated=req(f"/experiments/{exp['experiment_id']}/evaluate","POST",{})
                self.assertEqual(evaluated["decision"],"GO")
                listed=req("/experiments?project_id=PROJ")
                self.assertEqual(len(listed["experiments"]),1)
            finally:
                server.shutdown(); service.close()


if __name__=="__main__": unittest.main()
