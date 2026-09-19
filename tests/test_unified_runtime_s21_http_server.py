from __future__ import annotations

import json
import unittest
from http.client import HTTPConnection

from unified_runtime.http_api_server import HTTPServerConfig, UnifiedRuntimeHTTPServer
from unified_runtime.security_hardening import ProductionSecurityConfig, SECRET_ENV


class TestS21HTTPServer(unittest.TestCase):
    def _config(self):
        return ProductionSecurityConfig.from_env({"AI_OS_RUNTIME_MODE": "production", SECRET_ENV: "s21-secret"})

    def _call(self, server, *, token="token"):
        host, port = server.address
        conn = HTTPConnection(host, port, timeout=3)
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        conn.request("POST", "/api/runs", body=json.dumps({}).encode("utf-8"), headers=headers)
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        conn.close()
        return response.status, body

    def test_no_token_returns_401_over_real_http(self):
        with UnifiedRuntimeHTTPServer(
            self._config(),
            HTTPServerConfig(tls_terminated=True),
            authenticator=lambda token: True,
        ) as server:
            status, body = self._call(server, token=None)
        self.assertEqual(status, 401)
        self.assertIn("token_present", body["failures"])
        self.assertTrue(body["http_server_io_executed"])
        self.assertFalse(body["external_action_executed"])
        self.assertFalse(body["memory_write_executed"])

    def test_invalid_token_returns_401_over_real_http(self):
        with UnifiedRuntimeHTTPServer(
            self._config(),
            HTTPServerConfig(tls_terminated=True),
            authenticator=lambda token: token == "valid",
        ) as server:
            status, body = self._call(server, token="invalid")
        self.assertEqual(status, 401)
        self.assertIn("authenticated", body["failures"])

    def test_no_tls_returns_403_over_real_http(self):
        with UnifiedRuntimeHTTPServer(
            self._config(),
            HTTPServerConfig(tls_terminated=False),
            authenticator=lambda token: True,
        ) as server:
            status, body = self._call(server)
        self.assertEqual(status, 403)
        self.assertIn("tls_ready", body["failures"])

    def test_valid_token_and_trusted_tls_boundary_is_admitted(self):
        with UnifiedRuntimeHTTPServer(
            self._config(),
            HTTPServerConfig(tls_terminated=True),
            authenticator=lambda token: {"authenticated": token == "valid", "subject": "user-1"},
        ) as server:
            status, body = self._call(server, token="valid")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ADMITTED")
        self.assertEqual(body["authentication"]["subject"], "user-1")
        self.assertFalse(body["external_action_executed"])
        self.assertFalse(body["memory_write_executed"])

    def test_unsafe_external_action_is_forbidden(self):
        # The S21 transport does not accept an external-action field from callers.
        # The application gate itself remains tested by S20; HTTP wiring must not
        # create a bypass route.
        with UnifiedRuntimeHTTPServer(
            self._config(),
            HTTPServerConfig(tls_terminated=True),
            authenticator=lambda token: True,
        ) as server:
            host, port = server.address
            conn = HTTPConnection(host, port, timeout=3)
            conn.request(
                "POST",
                "/api/runs",
                body=json.dumps({"external_action_requested": True}).encode("utf-8"),
                headers={"Authorization": "Bearer token", "Content-Type": "application/json"},
            )
            response = conn.getresponse()
            body = json.loads(response.read().decode("utf-8"))
            conn.close()
        self.assertEqual(response.status, 403)
        self.assertIn("external_action_blocked", body["failures"])

    def test_memory_write_request_is_forbidden_over_real_http(self):
        with UnifiedRuntimeHTTPServer(
            self._config(),
            HTTPServerConfig(tls_terminated=True),
            authenticator=lambda token: True,
        ) as server:
            host, port = server.address
            conn = HTTPConnection(host, port, timeout=3)
            conn.request(
                "POST",
                "/api/runs",
                body=json.dumps({"memory_write_requested": True}).encode("utf-8"),
                headers={"Authorization": "Bearer token", "Content-Type": "application/json"},
            )
            response = conn.getresponse()
            body = json.loads(response.read().decode("utf-8"))
            conn.close()
        self.assertEqual(response.status, 403)
        self.assertIn("automatic_memory_write_blocked", body["failures"])
        self.assertFalse(body["memory_write_executed"])

    def test_malformed_authorization_returns_401_over_real_http(self):
        with UnifiedRuntimeHTTPServer(
            self._config(),
            HTTPServerConfig(tls_terminated=True),
            authenticator=lambda token: True,
        ) as server:
            host, port = server.address
            conn = HTTPConnection(host, port, timeout=3)
            conn.request("POST", "/api/runs", body=b"{}", headers={"Authorization": "Basic token"})
            response = conn.getresponse()
            body = json.loads(response.read().decode("utf-8"))
            conn.close()
        self.assertEqual(response.status, 401)
        self.assertIn("token_present", body["failures"])

    def test_malformed_json_does_not_bypass_security(self):
        with UnifiedRuntimeHTTPServer(
            self._config(),
            HTTPServerConfig(tls_terminated=False),
            authenticator=lambda token: True,
        ) as server:
            host, port = server.address
            conn = HTTPConnection(host, port, timeout=3)
            conn.request(
                "POST",
                "/api/runs",
                body=b"{not-json",
                headers={"Authorization": "Bearer token", "Content-Type": "application/json"},
            )
            response = conn.getresponse()
            body = json.loads(response.read().decode("utf-8"))
            conn.close()
        self.assertEqual(response.status, 403)
        self.assertIn("tls_ready", body["failures"])

    def test_wrong_method_still_hits_security_boundary(self):
        with UnifiedRuntimeHTTPServer(
            self._config(),
            HTTPServerConfig(tls_terminated=True),
            authenticator=lambda token: False,
        ) as server:
            host, port = server.address
            conn = HTTPConnection(host, port, timeout=3)
            conn.request("GET", "/api/runs", headers={"Authorization": "Bearer invalid"})
            response = conn.getresponse()
            body = json.loads(response.read().decode("utf-8"))
            conn.close()
        self.assertEqual(response.status, 401)
        self.assertIn("authenticated", body["failures"])


if __name__ == "__main__":
    unittest.main()
