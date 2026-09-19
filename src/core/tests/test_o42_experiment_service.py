import os
import tempfile
import unittest

from src.api import InProcessAPI
from src.service import ApplicationService
from src.experiments import ExperimentService
from src.experiment_store import ExperimentStore


class FakeRuntime:
    def __init__(self):
        self.memory = None
    def run(self, run_id, project_id, request, audience=None, goal=None, constraints=None, language="en"):
        return {
            "status": "COMPLETE",
            "run_id": run_id,
            "project_id": project_id,
            "decision_surface": {
                "recommendation": "Narrow workflow automation",
                "customer": audience,
                "problem": "Recurring manual workflow",
                "desired_outcome": "Reduce manual work",
                "opportunity_score": 6.0,
                "strategy_score": 7.7,
                "confidence": "medium",
                "evidence_boundary": "local_evidence_supported",
                "validation_experiment": {
                    "experiment_id": f"VAL-{run_id}",
                    "hypothesis": "Customers experience recurring manual work.",
                    "who": audience,
                    "sample_size": 10,
                    "method": "Interview 10 target customers.",
                    "measure": ["problem_confirmation", "high_intent"],
                    "success_threshold": {
                        "problem_confirmation": "At least 6/10",
                        "high_intent": "At least 3/10",
                    },
                    "decision_rule": "GO when both thresholds are met; otherwise REFINE.",
                    "timebox_days": 7,
                    "external_action_required": False,
                },
            },
        }
    def close(self):
        return None


class TestO42ExperimentService(unittest.TestCase):
    def test_run_to_experiment_to_decision(self):
        with tempfile.TemporaryDirectory() as td:
            jobs = os.path.join(td, "jobs.sqlite3")
            service = ApplicationService(db_path=jobs, runtime=FakeRuntime())
            api = InProcessAPI(service)
            created = api.post_run({
                "project_id": "PROJ-O42",
                "request": "Validate an AI opportunity",
                "audience": "Egyptian SMEs",
                "goal": "validate a lean opportunity",
                "constraints": ["low cost"],
                "language": "ar",
            })
            self.assertEqual(created["status"], "QUEUED")
            run = api.run_now(created["job_id"])
            self.assertEqual(run["status"], "COMPLETE")
            exp = api.create_experiment_from_run(created["job_id"])
            self.assertEqual(exp["status"], "READY")
            evidence = api.record_experiment_evidence(exp["experiment_id"], {
                "sample_size": 10,
                "metrics": {"problem_confirmation": 7, "high_intent": 4},
                "evidence_refs": ["INT-001", "INT-010"],
                "observations": [{"id": "INT-001", "note": "Recurring issue"}],
            })
            self.assertEqual(evidence["status"], "EVIDENCE_RECORDED")
            evaluated = api.evaluate_experiment(exp["experiment_id"])
            self.assertEqual(evaluated["decision"], "GO")
            self.assertEqual(evaluated["evaluation"]["decision"], "GO")
            service.close()

    def test_missing_evidence_does_not_produce_go(self):
        with tempfile.TemporaryDirectory() as td:
            store = ExperimentStore(os.path.join(td, "experiments.sqlite3"))
            svc = ExperimentService(store, jobs=type("J", (), {"get": lambda self, x: None})())
            exp = store.create({
                "experiment_id": "VAL-EMPTY", "sample_size": 10,
                "success_threshold": {"x": {"operator": ">=", "value": 6}},
            }, "PROJ")
            out = svc.evaluate("VAL-EMPTY")
            self.assertEqual(out["decision"], "INCONCLUSIVE")
            store.close()


if __name__ == "__main__":
    unittest.main()
