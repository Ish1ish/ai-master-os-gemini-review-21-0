import os, tempfile
from src.api import InProcessAPI
from src.service import ApplicationService

class SmokeRuntime:
    def run(self, run_id, project_id, request, audience=None, goal=None, constraints=None, language="en"):
        return {"status":"COMPLETE","run_id":run_id,"project_id":project_id,
                "decision_surface":{"recommendation":"O43 smoke","customer":audience,"problem":"Test pain",
                "desired_outcome":"Bounded result","opportunity_score":7.1,"strategy_score":8.2,
                "confidence":"medium","evidence_boundary":"local_evidence_supported",
                "validation_experiment":{"experiment_id":f"VAL-{run_id}","hypothesis":"Pain is real",
                "sample_size":10,"method":"Interview 10","success_threshold":{"problem_confirmation":"At least 6/10"},
                "decision_rule":"GO when threshold is met; otherwise REFINE.","external_action_required":False}}}
    def close(self): pass

def run_smoke():
    with tempfile.TemporaryDirectory() as td:
        s=ApplicationService(db_path=os.path.join(td,'jobs.sqlite3'),runtime=SmokeRuntime())
        api=InProcessAPI(s)
        sub=api.post_run({"project_id":"PROJ-O43","request":"smoke","audience":"Egyptian SMEs","goal":"validate","language":"ar"})
        api.run_now(sub["job_id"])
        exp=api.create_experiment_from_run(sub["job_id"])
        api.record_experiment_evidence(exp["experiment_id"],{"sample_size":10,"metrics":{"problem_confirmation":7},"evidence_refs":["INT-001","INT-010"]})
        out=api.evaluate_experiment(exp["experiment_id"])
        ctx=api.get_learning_context("PROJ-O43")
        s.close()
        assert out["decision"]=="GO"
        assert ctx["status"]=="READY"
        assert ctx["routing_guidance"]["preferred_action"]=="BOUNDED_NEXT_STEP"
        return {"status":"PASS","decision":out["decision"],"context_id":ctx["context_id"]}
if __name__ == '__main__': print(run_smoke())
