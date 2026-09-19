from __future__ import annotations

import os
import tempfile

from src.api import InProcessAPI
from src.service import ApplicationService


class SmokeRuntime:
    def run(self, run_id, project_id, request, audience=None, goal=None, constraints=None, language="en"):
        return {
            "status": "COMPLETE", "run_id": run_id, "project_id": project_id,
            "decision_surface": {
                "recommendation": "O42 smoke opportunity",
                "customer": audience,
                "problem": "Recurring workflow pain",
                "desired_outcome": "Reduce time cost",
                "opportunity_score": 6.2, "strategy_score": 7.4,
                "confidence": "medium", "evidence_boundary": "local_evidence_supported",
                "validation_experiment": {
                    "experiment_id": f"VAL-{run_id}", "hypothesis": "The problem is material.",
                    "sample_size": 10, "method": "Interview 10 customers",
                    "success_threshold": {"problem_confirmation": "At least 6/10", "high_intent": "At least 3/10"},
                    "decision_rule": "GO when both thresholds are met; otherwise REFINE.",
                    "external_action_required": False,
                },
            },
        }
    def close(self):
        pass


def run_smoke():
    with tempfile.TemporaryDirectory() as td:
        service = ApplicationService(db_path=os.path.join(td, "jobs.sqlite3"), runtime=SmokeRuntime())
        api = InProcessAPI(service)
        submitted = api.post_run({"project_id":"PROJ-O42","request":"smoke","audience":"Egyptian SMEs","goal":"validate","language":"ar"})
        completed = api.run_now(submitted["job_id"])
        experiment = api.create_experiment_from_run(submitted["job_id"])
        api.record_experiment_evidence(experiment["experiment_id"], {
            "sample_size":10,
            "metrics":{"problem_confirmation":7,"high_intent":4},
            "evidence_refs":["SMOKE-001","SMOKE-010"],
        })
        evaluated = api.evaluate_experiment(experiment["experiment_id"])
        service.close()
        assert completed["status"] == "COMPLETE"
        assert evaluated["decision"] == "GO"
        return {"status":"PASS", "decision":evaluated["decision"], "experiment_id":experiment["experiment_id"]}


if __name__ == "__main__":
    print(run_smoke())
