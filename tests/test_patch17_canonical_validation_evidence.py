import tempfile
import unittest

from unified_runtime.canonical_http_api import CanonicalHTTPAPI
from unified_runtime.integrated_runtime import RealUnifiedRuntime


def principal(*scopes, principal_id="validator-01"):
    return {
        "principal_id": principal_id,
        "principal": principal_id,
        "scopes": list(scopes),
        "authenticated": True,
    }


class _Entrypoint:
    def __init__(self, runtime):
        self.runtime = runtime


class TestPatch17CanonicalValidationEvidence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = RealUnifiedRuntime(self.tmp.name)
        self.api = CanonicalHTTPAPI(_Entrypoint(self.runtime))

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def _create_run(self, run_id="PATCH17-001"):
        return self.runtime.run(
            run_id=run_id,
            project_id="PATCH17-PROJECT",
            strategy_id="PATCH17-STRATEGY",
            intent="Validate a bounded opportunity",
        )

    def test_run_creates_durable_o42_experiment_and_stays_inconclusive_without_evidence(self):
        result = self._create_run()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["stages"]["EVALUATION"]["decision"], "INCONCLUSIVE")
        experiment_id = result["experiment"]["experiment_id"]
        stored = self.runtime.get_experiment(experiment_id)
        self.assertEqual(stored["run_id"], "PATCH17-001")
        self.assertEqual(stored["project_id"], "PATCH17-PROJECT")
        self.assertEqual(stored["decision"], "INCONCLUSIVE")
        self.assertEqual(stored["status"], "INCONCLUSIVE")
        self.assertIsNone(stored["evidence"])

    def test_o42_experiment_survives_runtime_restart(self):
        result = self._create_run(run_id="PATCH17-RESTART")
        experiment_id = result["experiment"]["experiment_id"]
        root = self.tmp.name
        self.runtime.close()
        self.runtime = RealUnifiedRuntime(root)
        self.api = CanonicalHTTPAPI(_Entrypoint(self.runtime))
        stored = self.runtime.get_experiment(experiment_id)
        self.assertEqual(stored["run_id"], "PATCH17-RESTART")
        self.assertEqual(stored["decision"], "INCONCLUSIVE")

    def test_validator_can_record_evidence_and_evaluate_go(self):
        result = self._create_run(run_id="PATCH17-GO")
        experiment_id = result["experiment"]["experiment_id"]
        validator = principal(
            "experiment:read",
            "experiment:write",
            "experiment:evaluate",
            "learning:read",
        )

        code, saved = self.api.handle(
            method="POST",
            path=f"/api/experiments/{experiment_id}/evidence",
            body={
                "sample_size": 10,
                "metrics": {"problem_confirmed": 8, "pilot_interest": 4},
                "evidence_refs": ["PATCH17-EV-1", "PATCH17-EV-2"],
            },
            principal=validator,
        )
        self.assertEqual(code, 200)
        self.assertEqual(saved["status"], "EVIDENCE_RECORDED")

        code, evaluated = self.api.handle(
            method="POST",
            path=f"/api/experiments/{experiment_id}/evaluate",
            body={},
            principal=validator,
        )
        self.assertEqual(code, 200)
        self.assertEqual(evaluated["decision"], "GO")
        self.assertEqual(evaluated["evaluation"]["decision"], "GO")

        code, context = self.api.handle(
            method="GET",
            path="/api/learning/context?project_id=PATCH17-PROJECT",
            body=None,
            principal=validator,
        )
        self.assertEqual(code, 200)
        self.assertEqual(context["status"], "READY")
        self.assertEqual(context["lessons"][0]["experiment_id"], experiment_id)
        self.assertEqual(context["lessons"][0]["decision"], "GO")

    def test_operator_cannot_write_validation_evidence(self):
        result = self._create_run(run_id="PATCH17-AUTH")
        experiment_id = result["experiment"]["experiment_id"]
        code, body = self.api.handle(
            method="POST",
            path=f"/api/experiments/{experiment_id}/evidence",
            body={"sample_size": 10, "metrics": {}, "evidence_refs": ["X"]},
            principal=principal(
                "run:submit",
                "run:read",
                "run:list",
                principal_id="operator-01",
            ),
        )
        self.assertEqual(code, 403)
        self.assertEqual(body["status"], "FORBIDDEN")
        self.assertEqual(body["required_scope"], "experiment:write")

    def test_missing_learning_project_is_bad_request(self):
        validator = principal("learning:read")
        code, body = self.api.handle(
            method="GET",
            path="/api/learning/context",
            body=None,
            principal=validator,
        )
        self.assertEqual(code, 400)
        self.assertEqual(body["reason"], "project_id_required")


if __name__ == "__main__":
    unittest.main()
