import unittest
from pathlib import Path

from unified_runtime.http_api_server import HTTPRequest, HTTPServerConfig, UnifiedRuntimeHTTPServer
from unified_runtime.security_hardening import ProductionSecurityConfig, SECRET_ENV
from unified_runtime.entrypoint import UnifiedRuntimeEntrypoint


class MockAuthenticator:
    def authenticate(self, token):
        if token == "valid-token":
            return {
                "status": "ALLOW",
                "authenticated": True,
                "principal": "test-user-01",
                "roles": ["operator"],
                "scopes": ["run:submit"],
                "auth_method": "signed-bearer",
            }
        return {
            "status": "BLOCKED_UNAUTHENTICATED",
            "authenticated": False,
        }


class RecordingEntrypoint:
    def __init__(self):
        self.calls = []

    def run(self, request, principal=None):
        self.calls.append(
            {
                "request": request,
                "principal": dict(principal or {}),
            }
        )
        return {
            "status": "PASS",
            "requested_by": (principal or {}).get("principal"),
        }


class TestHTTPDispatchAndIdentity(unittest.TestCase):
    def setUp(self):
        self.config = ProductionSecurityConfig.from_env(
            {
                "AI_OS_RUNTIME_MODE": "production",
                SECRET_ENV: "patch01-secret",
            }
        )
        self.valid_body = {
            "run_id": "r1",
            "project_id": "p1",
            "strategy_id": "s1",
            "intent": "test intent",
        }

    def _server(self, authenticator, entrypoint):
        return UnifiedRuntimeHTTPServer(
            config=self.config,
            server_config=HTTPServerConfig(tls_terminated=True),
            authenticator=authenticator,
            entrypoint=entrypoint,
        )

    def _request(self, token):
        return HTTPRequest(
            method="POST",
            path="/api/runs",
            headers={"Authorization": f"Bearer {token}"},
            tls_terminated=True,
        )

    def test_a_invalid_authentication_stops_before_entrypoint(self):
        entrypoint = RecordingEntrypoint()
        authenticator = MockAuthenticator().authenticate
        server = self._server(authenticator, entrypoint)
        req = self._request("bad-token")

        res = server.handle_http(
            method=req.method,
            path=req.path,
            headers=req.headers,
            body=self.valid_body,
        )

        self.assertEqual(res.status_code, 401)
        self.assertNotIn("application_response", res.body)
        self.assertEqual(entrypoint.calls, [])

    def test_b_valid_authentication_dispatches_to_entrypoint(self):
        entrypoint = RecordingEntrypoint()
        authenticator = MockAuthenticator().authenticate
        server = self._server(authenticator, entrypoint)
        req = self._request("valid-token")

        res = server.handle_http(
            method=req.method,
            path=req.path,
            headers=req.headers,
            body=self.valid_body,
        )

        self.assertEqual(res.status_code, 200)
        self.assertIn("application_response", res.body)
        self.assertEqual(len(entrypoint.calls), 1)

        call = entrypoint.calls[0]
        self.assertEqual(call["request"], self.valid_body)
        self.assertEqual(call["principal"]["principal"], "test-user-01")
        self.assertEqual(call["principal"]["roles"], ["operator"])
        self.assertEqual(call["principal"]["scopes"], ["run:submit"])
        self.assertEqual(
            res.body["application_response"]["requested_by"],
            "test-user-01",
        )

    def test_c_entrypoint_existing_runtime_failure_contract_remains_blocked(self):
        runtime_root = Path.cwd() / "PATCH_01_TEST_RUNTIME"
        runtime_root.mkdir(parents=True, exist_ok=True)

        entrypoint = UnifiedRuntimeEntrypoint(str(runtime_root))
        entrypoint.runtime.run = lambda **kwargs: (_ for _ in ()).throw(
            RuntimeError("simulated_unexpected_crash")
        )

        server = self._server(MockAuthenticator().authenticate, entrypoint)
        req = self._request("valid-token")

        res = server.handle_http(
            method=req.method,
            path=req.path,
            headers=req.headers,
            body=self.valid_body,
        )

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.body["application_response"]["status"], "BLOCKED")
        self.assertEqual(res.body["application_response"]["reason"], "runtime_error")
        self.assertEqual(
            res.body["application_response"]["error_type"],
            "RuntimeError",
        )

    def test_d_authentication_dictionary_is_not_returned_as_principal_payload(self):
        entrypoint = RecordingEntrypoint()
        server = self._server(MockAuthenticator().authenticate, entrypoint)
        req = self._request("valid-token")

        res = server.handle_http(
            method=req.method,
            path=req.path,
            headers=req.headers,
            body=self.valid_body,
        )

        app_res = res.body["application_response"]
        self.assertNotIn("roles", app_res)
        self.assertNotIn("scopes", app_res)
        self.assertNotIn("auth_method", app_res)
        self.assertNotIn("principal", app_res)
        self.assertEqual(app_res["requested_by"], "test-user-01")


if __name__ == "__main__":
    unittest.main()
