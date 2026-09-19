import unittest
from types import SimpleNamespace

from unified_runtime.canonical_http_api import CanonicalHTTPAPI
from unified_runtime.http_api_server import UnifiedRuntimeHTTPServer
from unified_runtime.http_security_adapter import HTTPResponse
from unified_runtime.integrated_runtime import RealUnifiedRuntime


class FakeRuntime:
    def __init__(self):
        self.calls = []

    def execute_governed_intent(self, intent_id, *, principal=None):
        self.calls.append(("execute", intent_id, dict(principal or {})))
        return {"status": "SUCCEEDED", "intent_id": intent_id}

    def list_approvals(self):
        self.calls.append(("list_approvals",))
        return [{"approval_id": "APR-1", "status": "PENDING"}]

    def get_approval(self, approval_id):
        self.calls.append(("get_approval", approval_id))
        return {
            "approval_id": approval_id,
            "status": "APPROVED",
        }

    def decide_approval(self, approval_id, *, principal, decision, reason):
        self.calls.append(
            (
                "decide_approval",
                approval_id,
                dict(principal),
                decision,
                reason,
            )
        )
        return {
            "status": "APPROVED",
            "approval_id": approval_id,
            "execution": {"status": "READY"},
        }

    def get_execution(self, execution_id):
        self.calls.append(("get_execution", execution_id))
        return {"status": "READY", "execution_id": execution_id}


class FakeEntrypoint:
    def __init__(self):
        self.runtime = FakeRuntime()
        self.calls = []

    def run(self, request, principal=None):
        self.calls.append(("run", dict(request), dict(principal or {})))
        return {"status": "WAITING_HUMAN_APPROVAL", "run_id": request["run_id"]}


class FakeOrchestrator:
    def __init__(self):
        self.calls = []

    def drive(self, intent_id, *, authz=None, principal=None):
        self.calls.append(
            {
                "intent_id": intent_id,
                "authz": authz,
                "principal": dict(principal or {}),
            }
        )
        gate = authz.authorize(principal, "job:execute")
        if gate.get("status") != "ALLOW":
            return gate
        return {"status": "SUCCEEDED", "intent_id": intent_id}


class FakeAdapter:
    def handle(self, request):
        return HTTPResponse(
            200,
            {
                "authentication": principal(
                    "run:submit",
                    principal_id="operator-01",
                ),
            },
        )


class FakeCanonicalAPI:
    def __init__(self):
        self.calls = []

    def handle(self, **kwargs):
        self.calls.append(kwargs)
        return 200, {"status": "CANONICAL"}


def principal(*scopes, principal_id="operator-01"):
    return {
        "principal_id": principal_id,
        "principal": principal_id,
        "scopes": list(scopes),
        "authenticated": True,
    }


class TestPatch05CanonicalHTTPAPI(unittest.TestCase):
    def setUp(self):
        self.entrypoint = FakeEntrypoint()
        self.api = CanonicalHTTPAPI(self.entrypoint)

    def test_submission_delegates_to_entrypoint_and_does_not_execute(self):
        code, result = self.api.handle(
            method="POST",
            path="/api/runs",
            body={
                "run_id": "RUN-1",
                "project_id": "P1",
                "strategy_id": "S1",
                "intent": "test",
            },
            principal=principal("run:submit"),
        )
        self.assertEqual(code, 200)
        self.assertEqual(result["status"], "WAITING_HUMAN_APPROVAL")
        self.assertEqual([c[0] for c in self.entrypoint.calls], ["run"])
        self.assertEqual(self.entrypoint.runtime.calls, [])

    def test_execution_uses_intent_id_and_existing_runtime_authority(self):
        code, result = self.api.handle(
            method="POST",
            path="/api/intents/INT-1/execute",
            body={},
            principal=principal("run:execute"),
        )
        self.assertEqual(code, 200)
        self.assertEqual(result["intent_id"], "INT-1")
        self.assertEqual(self.entrypoint.runtime.calls[0][0], "execute")
        self.assertEqual(self.entrypoint.runtime.calls[0][1], "INT-1")
        self.assertNotIn("authz", self.entrypoint.runtime.calls[0][2])

    def test_missing_principal_fails_closed(self):
        code, result = self.api.handle(
            method="POST",
            path="/api/runs",
            body={},
            principal={},
        )
        self.assertEqual(code, 401)
        self.assertEqual(result["status"], "UNAUTHORIZED")

    def test_missing_scope_is_forbidden(self):
        code, result = self.api.handle(
            method="POST",
            path="/api/intents/INT-1/execute",
            body={},
            principal=principal("run:read"),
        )
        self.assertEqual(code, 403)
        self.assertEqual(result["status"], "FORBIDDEN")

    def test_approval_list_and_lookup_delegate_to_runtime(self):
        code, result = self.api.handle(
            method="GET",
            path="/api/approvals",
            body=None,
            principal=principal("approval:read"),
        )
        self.assertEqual(code, 200)
        self.assertEqual(result["approvals"][0]["approval_id"], "APR-1")

        code, result = self.api.handle(
            method="GET",
            path="/api/approvals/APR-1",
            body=None,
            principal=principal("approval:read"),
        )
        self.assertEqual(code, 200)
        self.assertEqual(result["approval_id"], "APR-1")

        self.assertEqual(
            [c[0] for c in self.entrypoint.runtime.calls],
            ["list_approvals", "get_approval"],
        )

    def test_approval_decision_does_not_directly_execute(self):
        code, result = self.api.handle(
            method="POST",
            path="/api/approvals/APR-1/decision",
            body={"decision": "APPROVED", "reason": "approved"},
            principal=principal("approval:decide"),
        )
        self.assertEqual(code, 200)
        self.assertEqual(result["status"], "APPROVED")
        self.assertEqual(
            [c[0] for c in self.entrypoint.runtime.calls],
            ["decide_approval"],
        )

    def test_execution_read_is_read_only(self):
        code, result = self.api.handle(
            method="GET",
            path="/api/executions/EXE-1",
            body=None,
            principal=principal("run:read"),
        )
        self.assertEqual(code, 200)
        self.assertEqual(result["execution_id"], "EXE-1")
        self.assertEqual(
            self.entrypoint.runtime.calls,
            [("get_execution", "EXE-1")],
        )

    def test_unknown_canonical_route_is_not_found(self):
        code, result = self.api.handle(
            method="GET",
            path="/api/not-a-route",
            body=None,
            principal=principal("run:read"),
        )
        self.assertEqual(code, 404)
        self.assertEqual(result["status"], "NOT_FOUND")

    def test_explicit_false_authentication_fails_closed(self):
        code, result = self.api.handle(
            method="POST",
            path="/api/runs",
            body={},
            principal={
                "principal_id": "spoofed",
                "principal": "spoofed",
                "authenticated": False,
                "scopes": ["run:submit"],
            },
        )
        self.assertEqual(code, 401)
        self.assertEqual(result["status"], "UNAUTHORIZED")

    def test_runtime_execution_passes_scope_authorizer_into_o45(self):
        runtime = RealUnifiedRuntime.__new__(RealUnifiedRuntime)
        orchestrator = FakeOrchestrator()
        runtime._o45_bundle = (
            None,
            None,
            None,
            None,
            None,
            None,
            orchestrator,
        )
        result = runtime.execute_governed_intent(
            "INT-1",
            principal=principal("job:execute", principal_id="worker-01"),
        )
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertIsNotNone(orchestrator.calls[0]["authz"])

    def test_runtime_execution_denies_without_job_execute_scope(self):
        runtime = RealUnifiedRuntime.__new__(RealUnifiedRuntime)
        orchestrator = FakeOrchestrator()
        runtime._o45_bundle = (
            None,
            None,
            None,
            None,
            None,
            None,
            orchestrator,
        )
        result = runtime.execute_governed_intent(
            "INT-1",
            principal=principal("run:execute", principal_id="operator-01"),
        )
        self.assertEqual(result["status"], "DENY")
        self.assertEqual(result["required_scope"], "job:execute")

    def test_http_server_preserves_non_api_entrypoint_routing(self):
        server = UnifiedRuntimeHTTPServer.__new__(UnifiedRuntimeHTTPServer)
        server.server_config = SimpleNamespace(tls_terminated=False)
        server.adapter = FakeAdapter()
        server.entrypoint = self.entrypoint
        server.canonical_api = FakeCanonicalAPI()
        response = server.handle_http(
            method="POST",
            path="/legacy",
            headers={},
            body={"run_id": "RUN-LEGACY"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.body["application_response"]["status"],
            "WAITING_HUMAN_APPROVAL",
        )
        self.assertEqual(server.canonical_api.calls, [])

    def test_http_server_routes_api_paths_to_canonical_adapter(self):
        server = UnifiedRuntimeHTTPServer.__new__(UnifiedRuntimeHTTPServer)
        server.server_config = SimpleNamespace(tls_terminated=False)
        server.adapter = FakeAdapter()
        server.entrypoint = self.entrypoint
        server.canonical_api = FakeCanonicalAPI()
        response = server.handle_http(
            method="POST",
            path="/api/runs",
            headers={},
            body={"run_id": "RUN-CANONICAL"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.body["application_response"]["status"],
            "CANONICAL",
        )
        self.assertEqual(self.entrypoint.calls, [])
        self.assertEqual(server.canonical_api.calls[0]["path"], "/api/runs")


if __name__ == "__main__":
    unittest.main()
