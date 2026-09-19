import os
import tempfile
import unittest

from src.api import InProcessAPI
from src.service import ApplicationService


class SmokeRuntime:
    def __init__(self, decision="GO"):
        self.decision = decision
    def run(self, run_id, project_id, request, audience=None, goal=None, constraints=None, language="en"):
        return {
            "status": "COMPLETE", "run_id": run_id, "project_id": project_id,
            "decision_surface": {
                "recommendation": "Learning loop test",
                "customer": audience,
                "problem": "Recurring test problem",
                "desired_outcome": "Evidence-backed result",
                "opportunity_score": 7.0,
                "strategy_score": 8.0,
                "confidence": "medium",
                "evidence_boundary": "local_evidence_supported",
                "validation_experiment": {
                    "experiment_id": f"VAL-{run_id}",
                    "hypothesis": "The recurring problem is material.",
                    "sample_size": 10,
                    "success_threshold": {"problem_confirmation": {"operator": ">=", "value": 6}},
                    "decision_rule": "GO when threshold passes; otherwise REFINE.",
                    "external_action_required": False,
                },
            },
        }
    def close(self):
        pass


class TestO43LearningLoop(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.service = ApplicationService(db_path=os.path.join(self.td.name, "jobs.sqlite3"), runtime=SmokeRuntime())
        self.api = InProcessAPI(self.service)

    def tearDown(self):
        self.service.close()
        self.td.cleanup()

    def _conclude(self, project="P1", metric=7, refs=None):
        refs = refs or ["EV-001", "EV-002"]
        sub = self.api.post_run({"project_id": project, "request": "learn", "audience": "SMEs", "goal": "test"})
        self.api.run_now(sub["job_id"])
        exp = self.api.create_experiment_from_run(sub["job_id"])
        self.api.record_experiment_evidence(exp["experiment_id"], {"sample_size": 10, "metrics": {"problem_confirmation": metric}, "evidence_refs": refs})
        return self.api.evaluate_experiment(exp["experiment_id"])

    def test_go_outcome_becomes_bounded_next_step_context(self):
        evaluated = self._conclude(metric=7)
        self.assertEqual(evaluated["decision"], "GO")
        ctx = self.api.get_learning_context("P1")
        self.assertEqual(ctx["status"], "READY")
        self.assertEqual(ctx["routing_guidance"]["preferred_action"], "BOUNDED_NEXT_STEP")
        self.assertTrue(ctx["lessons"])
        self.assertIn("durable_memory_lessons", ctx)

    def test_inconclusive_is_not_decision_driving_learning(self):
        sub = self.api.post_run({"project_id": "P2", "request": "learn", "audience": "SMEs", "goal": "test"})
        self.api.run_now(sub["job_id"])
        exp = self.api.create_experiment_from_run(sub["job_id"])
        self.api.record_experiment_evidence(exp["experiment_id"], {"sample_size": 2, "metrics": {}, "evidence_refs": ["EV-001"]})
        evaluated = self.api.evaluate_experiment(exp["experiment_id"])
        self.assertEqual(evaluated["decision"], "INCONCLUSIVE")
        ctx = self.api.get_learning_context("P2")
        self.assertEqual(ctx["status"], "EMPTY")
        self.assertEqual(ctx["routing_guidance"]["preferred_action"], "COLLECT_INITIAL_EVIDENCE")

    def test_no_go_routes_to_next_hypothesis(self):
        service = ApplicationService(db_path=os.path.join(self.td.name, "jobs2.sqlite3"), runtime=SmokeRuntime())
        api = InProcessAPI(service)
        sub = api.post_run({"project_id": "P3", "request": "learn", "audience": "SMEs", "goal": "test"})
        api.run_now(sub["job_id"])
        exp = api.create_experiment_from_run(sub["job_id"])
        # Inject an explicit NO-GO rule through the stored definition using the public record/evaluate contract.
        record = api.record_experiment_evidence(exp["experiment_id"], {"sample_size": 10, "metrics": {"problem_confirmation": 0}, "evidence_refs": ["EV-NG-1", "EV-NG-2"]})
        record["definition"]["no_go_thresholds"] = {"problem_confirmation": {"operator": "<", "value": 3, "reason": "Problem signal too weak."}}
        # Persist the definition update only through the test store; this isolates the decision semantics test.
        service.experiments.store.conn.execute("UPDATE experiments SET definition_json=? WHERE experiment_id=?", (__import__('json').dumps(record["definition"]), exp["experiment_id"]))
        service.experiments.store.conn.commit()
        evaluated = api.evaluate_experiment(exp["experiment_id"])
        self.assertEqual(evaluated["decision"], "NO-GO")
        ctx = api.get_learning_context("P3")
        self.assertEqual(ctx["routing_guidance"]["preferred_action"], "ROUTE_TO_NEXT_HYPOTHESIS")
        service.close()

    def test_current_experiment_can_be_excluded_from_context(self):
        evaluated = self._conclude(project="P4", metric=7)
        exp_id = evaluated["experiment_id"]
        ctx = self.api.get_learning_context("P4", current_experiment_id=exp_id)
        self.assertEqual(ctx["lessons"], [])
        self.assertEqual(ctx["retrieval_policy"]["exclude_inconclusive"], True)

    def test_learning_context_is_project_scoped(self):
        self._conclude(project="P5", metric=7)
        self._conclude(project="P6", metric=7)
        ctx = self.api.get_learning_context("P5")
        self.assertTrue(all(x["experiment_id"] for x in ctx["lessons"]))
        other = self.api.get_learning_context("P6")
        self.assertNotEqual({x["experiment_id"] for x in ctx["lessons"]}, {x["experiment_id"] for x in other["lessons"]})


if __name__ == "__main__":
    unittest.main()
