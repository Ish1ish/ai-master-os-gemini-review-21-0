from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from unified_runtime.security_boundary import ProductionSecurityBoundary, SecurityRequest
from unified_runtime.security_hardening import ProductionSecurityConfig, SECRET_ENV


class TestS19SecurityBoundary(unittest.TestCase):
    def _production(self, auth=None):
        cfg = ProductionSecurityConfig.from_env({"AI_OS_RUNTIME_MODE": "production", SECRET_ENV: "test-secret-123456"})
        return ProductionSecurityBoundary(cfg, authenticator=auth)

    def _request(self, **kwargs):
        base = dict(method="POST", path="/api/runs", bearer_token="token", tls_terminated=True)
        base.update(kwargs)
        return SecurityRequest(**base)

    def test_production_without_authenticator_fails_closed(self):
        result = self._production().admit(self._request())
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("authenticated", result["failures"])

    def test_valid_auth_and_tls_are_admitted(self):
        result = self._production(lambda token: {"authenticated": token == "token", "subject": "user-1"}).admit(self._request())
        self.assertEqual(result["status"], "ADMITTED")
        self.assertEqual(result["authentication"]["subject"], "user-1")

    def test_o36_signed_bearer_authenticator_is_admitted(self):
        from core.src.auth import build_default_production_authenticator

        with patch.dict(os.environ, {"AI_OS_IDENTITY_SIGNING_SECRET": "test-secret-123456"}, clear=False):
            authenticator, identity = build_default_production_authenticator()
            token = identity.issue_token("operator-01")["token"]
        result = self._production(lambda bearer_token: authenticator.authenticate({"bearer_token": bearer_token})).admit(self._request(bearer_token=token))
        self.assertEqual(result["status"], "ADMITTED")
        self.assertEqual(result["authentication"]["status"], "ALLOW")
        self.assertIs(result["authentication"]["authenticated"], True)
        self.assertEqual(result["authentication"]["principal"], "operator-01")

    def test_missing_token_blocks(self):
        result = self._production(lambda token: True).admit(self._request(bearer_token=""))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("token_present", result["failures"])

    def test_tls_is_required_in_production(self):
        result = self._production(lambda token: True).admit(self._request(tls_terminated=False))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("tls_ready", result["failures"])

    def test_external_action_is_blocked(self):
        result = self._production(lambda token: True).admit(self._request(external_action_requested=True))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("external_action_blocked", result["failures"])
        self.assertFalse(result["external_action_executed"])

    def test_memory_write_is_blocked(self):
        result = self._production(lambda token: True).admit(self._request(memory_write_requested=True))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("automatic_memory_write_blocked", result["failures"])
        self.assertFalse(result["memory_write_executed"])

    def test_authenticator_exception_fails_closed(self):
        def boom(token):
            raise RuntimeError("boom")
        result = self._production(boom).admit(self._request())
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["authentication"]["status"], "BLOCKED_AUTHENTICATOR_ERROR")

    def test_development_can_admit_without_auth(self):
        cfg = ProductionSecurityConfig.from_env({"AI_OS_RUNTIME_MODE": "development"})
        result = ProductionSecurityBoundary(cfg).admit(self._request(bearer_token="", tls_terminated=False))
        self.assertEqual(result["status"], "ADMITTED")
        self.assertEqual(result["authentication"]["status"], "BYPASSED_DEVELOPMENT_ONLY")

    def test_empty_path_fails_closed(self):
        result = self._production(lambda token: True).admit(self._request(path=""))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("path_present", result["failures"])


if __name__ == "__main__":
    unittest.main()
