import inspect
import json
import threading
import unittest
from http.client import HTTPConnection

from unified_runtime.canonical_http_api import CanonicalHTTPAPI
from unified_runtime.http_api_server import HTTPServerConfig, UnifiedRuntimeHTTPServer
from unified_runtime.security_hardening import ProductionSecurityConfig


TOKEN_PRINCIPALS = {
    "token-operator": {
        "status": "ALLOW",
        "authenticated": True,
        "principal": "operator-01",
        "scopes": [
            "run:submit",
            "run:read",
            "run:list",
            "run:cancel",
            "run:execute",
            "job:execute",
            "approval:read",
            "approval:decide",
        ],
        "roles": ["operator"],
    },
    "token-viewer": {
        "status": "ALLOW",
        "authenticated": True,
        "principal": "viewer-01",
        "scopes": ["run:read"],
        "roles": ["viewer"],
    },
}


def build_test_security_config():
    """Build a secure test config without depending on optional constructor knobs."""
    params = inspect.signature(ProductionSecurityConfig).parameters
    kwargs = {}
    for name in params:
        if name == "mode":
            kwargs[name] = "development"
        elif name in {"require_authentication", "authentication_required"}:
            kwargs[name] = True
        elif name in {"require_tls", "tls_required"}:
            kwargs[name] = True
        elif name in {"identity_secret", "secret", "runtime_secret"}:
            kwargs[name] = "patch06-test-secret"
        elif name == "identity_signing_secret_present":
            kwargs[name] = True
        elif name == "external_actions_enabled":
            kwargs[name] = False
        elif name == "automatic_memory_write":
            kwargs[name] = False
    config = ProductionSecurityConfig(**kwargs)
    for name, value in (
        ("mode", "development"),
        ("require_authentication", True),
        ("require_tls", True),
    ):
        if hasattr(config, name):
            try:
                setattr(config, name, value)
            except (AttributeError, TypeError):
                pass
    return config


def authenticator_for_token(token):
    value = TOKEN_PRINCIPALS.get(token)
    if value is None:
        return {
            "status": "UNAUTHENTICATED",
            "authenticated": False,
        }
    return dict(value)


class RecordingRuntime:
    def __init__(self):
        self.calls = []
        self.execute_override = None

    def execute_governed_intent(self, intent_id, *, principal=None):
        self.calls.append(
            (
                "execute",
                intent_id,
                dict(principal or {}),
            )
        )
        if self.execute_override is not None:
            result = dict(self.execute_override)
            self.execute_override = None
            return result
        return {
            "status": "PENDING",
            "reason": "approval_required",
            "intent_id": intent_id,
        }

    def list_approvals(self):
        self.calls.append(("list_approvals",))
        return [
            {
                "approval_id": "APR-1",
                "status": "PENDING",
                "run_id": "RUN-1",
            }
        ]

    def get_approval(self, approval_id):
        self.calls.append(("get_approval", approval_id))
        if approval_id != "APR-1":
            return {
                "status": "NOT_FOUND",
                "approval_id": approval_id,
            }
        return {
            "status": "PENDING",
            "approval_id": approval_id,
            "run_id": "RUN-1",
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
            "decided_by": principal.get("principal_id") or principal.get("principal"),
            "execution": {"status": "READY"},
        }

    def get_execution(self, execution_id):
        self.calls.append(("get_execution", execution_id))
        if execution_id != "EXE-1":
            return {
                "status": "NOT_FOUND",
                "execution_id": execution_id,
            }
        return {
            "status": "READY",
            "execution_id": execution_id,
            "run_id": "RUN-1",
        }


class RecordingEntrypoint:
    def __init__(self):
        self.runtime = RecordingRuntime()
        self.calls = []

    def run(self, request, principal=None):
        self.calls.append(
            (
                "run",
                dict(request),
                dict(principal or {}),
            )
        )
        return {
            "status": "WAITING_HUMAN_APPROVAL",
            "run_id": request.get("run_id", "RUN-1"),
        }


class TestS21CanonicalSocketParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entrypoint = RecordingEntrypoint()
        cls.server = UnifiedRuntimeHTTPServer(
            build_test_security_config(),
            server_config=HTTPServerConfig(
                host="127.0.0.1",
                port=0,
                tls_terminated=True,
            ),
            authenticator=authenticator_for_token,
            entrypoint=cls.entrypoint,
        )
        cls.address = cls.server.start()
        cls._server_started = True

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "_server_started", False):
            cls.server.shutdown()

    def request(self, method, path, *, token=None, body=None):
        connection = HTTPConnection(self.address[0], self.address[1], timeout=5)
        headers = {
            "Connection": "close",
        }
        payload = None
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(payload))
        connection.request(method, path, body=payload, headers=headers)
        response = connection.getresponse()
        raw = response.read()
        status_code = response.status
        connection.close()
        parsed = json.loads(raw.decode("utf-8"))
        return status_code, parsed

    def test_socket_live_missing_token_returns_401(self):
        for method, path in (
            ("POST", "/api/runs"),
            ("GET", "/api/approvals"),
            ("POST", "/api/intents/INT-1/execute"),
        ):
            with self.subTest(method=method, path=path):
                status_code, payload = self.request(method, path, body={})
                self.assertEqual(status_code, 401)
                self.assertEqual(payload["status"], "BLOCKED")
                self.assertIn("token_present", payload["failures"])

    def test_socket_live_invalid_token_returns_401(self):
        status_code, payload = self.request(
            "GET",
            "/api/approvals",
            token="invalid-token",
        )
        self.assertEqual(status_code, 401)
        self.assertEqual(payload["status"], "BLOCKED")
        self.assertIn("authenticated", payload["failures"])

    def test_socket_live_insufficient_scope_returns_403(self):
        status_code, payload = self.request(
            "POST",
            "/api/intents/INT-1/execute",
            token="token-viewer",
            body={},
        )
        self.assertEqual(status_code, 403)
        self.assertEqual(payload["status"], "ADMITTED")
        self.assertEqual(
            payload["application_response"]["status"],
            "FORBIDDEN",
        )

    def test_socket_authenticated_principal_reaches_canonical_submit(self):
        self.entrypoint.calls.clear()
        status_code, payload = self.request(
            "POST",
            "/api/runs",
            token="token-operator",
            body={
                "run_id": "RUN-SOCKET-1",
                "project_id": "P1",
                "strategy_id": "S1",
                "intent": "socket parity",
            },
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(
            payload["application_response"]["status"],
            "WAITING_HUMAN_APPROVAL",
        )
        self.assertEqual(len(self.entrypoint.calls), 1)
        _, _, principal = self.entrypoint.calls[0]
        self.assertEqual(principal["principal_id"], "operator-01")
        self.assertIn("run:submit", principal["scopes"])

    def test_socket_api_unknown_and_malformed_routes_return_404_without_legacy_fallback(self):
        self.entrypoint.calls.clear()
        paths = (
            "/api/runs_malformed",
            "/api/run",
            "/api/approvals/foo/bar",
            "/api/approvals/abc/def/decision",
        )
        for path in paths:
            with self.subTest(path=path):
                status_code, payload = self.request(
                    "POST",
                    path,
                    token="token-operator",
                    body={},
                )
                self.assertEqual(status_code, 404)
                self.assertEqual(
                    payload["application_response"]["status"],
                    "NOT_FOUND",
                )
        self.assertEqual(self.entrypoint.calls, [])

    def test_socket_non_api_legacy_routing_is_preserved(self):
        self.entrypoint.calls.clear()
        status_code, payload = self.request(
            "POST",
            "/legacy-endpoint",
            token="token-operator",
            body={"run_id": "RUN-LEGACY"},
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(
            payload["application_response"]["status"],
            "WAITING_HUMAN_APPROVAL",
        )
        self.assertEqual(len(self.entrypoint.calls), 1)

    def test_socket_approval_decision_uses_authenticated_actor(self):
        self.entrypoint.runtime.calls.clear()
        status_code, payload = self.request(
            "POST",
            "/api/approvals/APR-1/decision",
            token="token-operator",
            body={
                "decision": "APPROVED",
                "reason": "accepted",
                "decided_by": "spoofed-user",
                "operator_id": "spoofed-operator",
            },
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(
            payload["application_response"]["decided_by"],
            "operator-01",
        )
        call = self.entrypoint.runtime.calls[-1]
        self.assertEqual(call[0], "decide_approval")
        self.assertEqual(call[2]["principal_id"], "operator-01")
        self.assertEqual(len(call[2]["scopes"]), len(set(call[2]["scopes"])))

    def test_socket_execution_route_preserves_intent_id_and_pending_semantics(self):
        self.entrypoint.runtime.calls.clear()
        status_code, payload = self.request(
            "POST",
            "/api/intents/INT-SOCKET-1/execute",
            token="token-operator",
            body={},
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(
            payload["application_response"]["status"],
            "PENDING",
        )
        call = self.entrypoint.runtime.calls[-1]
        self.assertEqual(call[0], "execute")
        self.assertEqual(call[1], "INT-SOCKET-1")
        self.assertEqual(call[2]["principal_id"], "operator-01")

    def test_socket_execution_conflict_maps_to_409(self):
        class ConflictRuntime(RecordingRuntime):
            def execute_governed_intent(self, intent_id, *, principal=None):
                return {
                    "status": "CONFLICT",
                    "reason": "idempotency_key_reused_with_different_request",
                }

        original = self.entrypoint.runtime
        original.execute_override = {
            "status": "CONFLICT",
            "reason": "idempotency_key_reused_with_different_request",
        }
        try:
            status_code, payload = self.request(
                "POST",
                "/api/intents/INT-1/execute",
                token="token-operator",
                body={},
            )
        finally:
            original.execute_override = None
        self.assertEqual(status_code, 409)
        self.assertEqual(
            payload["application_response"]["status"],
            "CONFLICT",
        )

    def test_direct_canonical_adapter_missing_authentication_state_fails_closed(self):
        entrypoint = RecordingEntrypoint()
        api = CanonicalHTTPAPI(entrypoint)
        status_code, payload = api.handle(
            method="POST",
            path="/api/runs",
            body={
                "run_id": "RUN-FAIL-CLOSED",
                "project_id": "P1",
                "strategy_id": "S1",
                "intent": "missing authentication marker",
            },
            principal={
                "principal_id": "operator-01",
                "scopes": ["run:submit"],
            },
        )
        self.assertEqual(status_code, 401)
        self.assertEqual(payload["status"], "UNAUTHORIZED")
        self.assertEqual(entrypoint.calls, [])


if __name__ == "__main__":
    unittest.main()
