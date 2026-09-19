import unittest

from core.src.auth import build_default_production_authenticator
from unified_runtime.security_boundary import ProductionSecurityBoundary, SecurityRequest
from unified_runtime.security_hardening import ProductionSecurityConfig


class TestS26O36AuthenticatorCallableContract(unittest.TestCase):
    def test_default_authenticator_is_callable_with_bearer_token(self):
        auth, identity = build_default_production_authenticator()
        token = identity.issue_token("operator-01")["token"]
        result = auth(token)
        self.assertEqual(result["status"], "ALLOW")
        self.assertTrue(result["authenticated"])
        self.assertEqual(result["principal"], "operator-01")
        self.assertEqual(result["auth_method"], "signed-bearer")

    def test_s19_boundary_accepts_default_o36_authenticator(self):
        auth, identity = build_default_production_authenticator()
        token = identity.issue_token("operator-01")["token"]
        config = ProductionSecurityConfig.from_env({"AI_OS_RUNTIME_MODE": "staging", "AI_OS_IDENTITY_SIGNING_SECRET": "s26-test-secret"})
        boundary = ProductionSecurityBoundary(config, authenticator=auth)
        result = boundary.admit(SecurityRequest(
            method="POST",
            path="/api/runs",
            bearer_token=token,
            tls_terminated=True,
        ))
        self.assertEqual(result["status"], "ADMITTED")
        self.assertTrue(result["authentication"]["authenticated"])
        self.assertEqual(result["authentication"]["principal"], "operator-01")
        self.assertFalse(result["external_action_executed"])
        self.assertFalse(result["memory_write_executed"])
