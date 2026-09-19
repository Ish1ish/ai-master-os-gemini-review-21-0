import os
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection

from src.api import InProcessAPI
from src.http_server import O32HTTPServer
from src.service import ApplicationService


class Runtime:
    def run(self, run_id, project_id, request, audience=None, goal=None, constraints=None, language="en"):
        return {"status":"COMPLETE","run_id":run_id,"project_id":project_id,"decision_surface":{
            "recommendation":"HTTP learning test","customer":audience,"problem":"Recurring problem","desired_outcome":"Outcome",
            "opportunity_score":6,"strategy_score":7.7,"confidence":"medium","evidence_boundary":"local_evidence_supported",
            "validation_experiment":{"experiment_id":f"VAL-{run_id}","hypothesis":"Problem is real","sample_size":10,
            "success_threshold":{"problem_confirmation":{"operator":">=","value":6}},"external_action_required":False}}}
    def close(self): pass


class TestO43HTTPAPI(unittest.TestCase):
    def test_learning_context_http_surface(self):
        with tempfile.TemporaryDirectory() as td:
            service=ApplicationService(db_path=os.path.join(td,"jobs.sqlite3"), runtime=Runtime())
            api=InProcessAPI(service)
            sub=api.post_run({"project_id":"HTTP-O43","request":"smoke"})
            api.run_now(sub["job_id"])
            exp=api.create_experiment_from_run(sub["job_id"])
            api.record_experiment_evidence(exp["experiment_id"], {"sample_size":10,"metrics":{"problem_confirmation":7},"evidence_refs":["HTTP-1","HTTP-2"]})
            api.evaluate_experiment(exp["experiment_id"])
            server=O32HTTPServer(api, host="127.0.0.1", port=0, require_auth=False)
            port=server.server.server_address[1]
            t=threading.Thread(target=server.start, daemon=True); t.start(); time.sleep(0.05)
            try:
                conn=HTTPConnection("127.0.0.1", port, timeout=5)
                conn.request("GET", "/learning/context?project_id=HTTP-O43")
                resp=conn.getresponse(); body=resp.read().decode()
                self.assertEqual(resp.status, 200)
                self.assertIn('BOUNDED_NEXT_STEP', body)
                conn.close()
            finally:
                server.shutdown(); service.close(); t.join(timeout=2)


if __name__ == "__main__": unittest.main()
