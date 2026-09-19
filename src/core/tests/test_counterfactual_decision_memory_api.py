import os
import tempfile
import unittest

from src.api import InProcessAPI
from src.service import ApplicationService


class TestCounterfactualDecisionMemoryAPI(unittest.TestCase):
    def test_record_observe_and_context_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            service = ApplicationService(
                db_path=os.path.join(td, "jobs.sqlite3"),
                experiments_db_path=os.path.join(td, "experiments.sqlite3"),
            )
            try:
                api = InProcessAPI(service)
                prediction = {
                    "status":"REVIEW","project_id":"P1","requested_by":"operator",
                    "decision":"REVIEW","risk":"HIGH","plan_hash":"PLAN-API-1","side_effects":"NONE",
                    "actions":[],"summary":{"estimated_approvals":1},
                }
                recorded = api.record_counterfactual_prediction({"project_id":"P1","requested_by":"operator","prediction":prediction})
                self.assertTrue(recorded["prediction_id"].startswith("CFP-"))
                observed = api.observe_counterfactual_outcome({"prediction_id":recorded["prediction_id"],"actual":{"decision":"REVIEW","risk":"HIGH"}})
                self.assertEqual(observed["learning"]["calibration"], "EXACT_MATCH")
                ctx = api.get_counterfactual_memory("P1")
                self.assertEqual(ctx["observed_count"], 1)
            finally:
                service.close()

    def test_side_effectful_prediction_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            service = ApplicationService(db_path=os.path.join(td,"jobs.sqlite3"), experiments_db_path=os.path.join(td,"experiments.sqlite3"))
            try:
                out = service.record_counterfactual_prediction({
                    "project_id":"P1","requested_by":"operator",
                    "prediction":{"decision":"REVIEW","risk":"HIGH","plan_hash":"X","side_effects":"UNKNOWN"}
                })
                self.assertEqual(out["status"], "BLOCK") if "status" in out else self.fail("expected ValueError boundary")
            except ValueError:
                pass
            finally:
                service.close()

if __name__ == "__main__":
    unittest.main()
