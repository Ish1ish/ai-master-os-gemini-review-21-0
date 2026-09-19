from __future__ import annotations

import unittest

from unified_runtime.http_security_adapter import HTTPProductionSecurityAdapter, HTTPRequest
from unified_runtime.security_hardening import ProductionSecurityConfig, SECRET_ENV


class TestS20HTTPSecurityAdapter(unittest.TestCase):
    def _adapter(self, auth=None):
        cfg = ProductionSecurityConfig.from_env({"AI_OS_RUNTIME_MODE": "production", SECRET_ENV: "s20-secret"})
        return HTTPProductionSecurityAdapter(cfg, authenticator=auth)

    def _request(self, **kwargs):
        base = dict(method="POST", path="/api/runs", headers={"Authorization": "Bearer token"}, tls_terminated=True)
        base.update(kwargs)
        return HTTPRequest(**base)

    def test_valid_authenticated_request_is_accepted(self):
        adapter = self._adapter(lambda token: {"authenticated": token == "token", "subject": "user-1"})
        response = adapter.handle(self._request())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body["status"], "ADMITTED")
        self.assertEqual(response.body["authentication"]["subject"], "user-1")

    def test_missing_bearer_token_returns_401(self):
        adapter = self._adapter(lambda token: True)
        response = adapter.handle(self._request(headers={}))
        self.assertEqual(response.status_code, 401)
        self.assertIn("token_present", response.body["failures"])

    def test_invalid_authentication_returns_401(self):
        adapter = self._adapter(lambda token: False)
        response = adapter.handle(self._request())
        self.assertEqual(response.status_code, 401)
        self.assertIn("authenticated", response.body["failures"])

    def test_missing_tls_returns_403(self):
        adapter = self._adapter(lambda token: True)
        response = adapter.handle(self._request(tls_terminated=False))
        self.assertEqual(response.status_code, 403)
        self.assertIn("tls_ready", response.body["failures"])

    def test_external_action_is_403(self):
        adapter = self._adapter(lambda token: True)
        response = adapter.handle(self._request(external_action_requested=True))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.body["external_action_executed"])

    def test_memory_write_is_403(self):
        adapter = self._adapter(lambda token: True)
        response = adapter.handle(self._request(memory_write_requested=True))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.body["memory_write_executed"])

    def test_development_mode_can_bypass_auth_only(self):
        cfg = ProductionSecurityConfig.from_env({"AI_OS_RUNTIME_MODE": "development"})
        adapter = HTTPProductionSecurityAdapter(cfg)
        response = adapter.handle(self._request(headers={}, tls_terminated=False))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body["authentication"]["status"], "BYPASSED_DEVELOPMENT_ONLY")

    def test_malformed_authorization_is_not_treated_as_bearer(self):
        adapter = self._adapter(lambda token: True)
        response = adapter.handle(self._request(headers={"Authorization": "Basic token"}))
        self.assertEqual(response.status_code, 401)
        self.assertIn("token_present", response.body["failures"])

    def test_adapter_does_not_perform_http_io(self):
        adapter = self._adapter(lambda token: True)
        response = adapter.handle(self._request())
        self.assertFalse(response.body["http_io_executed"])
        self.assertEqual(response.body["http_adapter_version"], "1.0")


if __name__ == "__main__":
    unittest.main()
