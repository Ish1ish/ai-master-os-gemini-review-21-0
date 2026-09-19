from __future__ import annotations

import unittest

from unified_runtime.security_hardening import ProductionSecurityConfig, SECRET_ENV


class TestS22_1StagingSecurity(unittest.TestCase):
    def _env(self, **extra):
        env = {"AI_OS_RUNTIME_MODE": "staging", SECRET_ENV: "staging-test-secret"}
        env.update(extra)
        return env

    def test_staging_requires_authentication(self):
        config = ProductionSecurityConfig.from_env(self._env())
        self.assertTrue(config.require_authentication)
        self.assertEqual(config.validate()["status"], "READY")

    def test_staging_requires_tls(self):
        config = ProductionSecurityConfig.from_env(self._env())
        self.assertTrue(config.require_tls)
        self.assertEqual(config.validate()["status"], "READY")

    def test_staging_requires_identity_secret(self):
        env = self._env()
        env.pop(SECRET_ENV)
        config = ProductionSecurityConfig.from_env(env)
        result = config.validate()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("secure_runtime_secret_present", result["failures"])

    def test_staging_missing_secure_flags_cannot_be_ready(self):
        config = ProductionSecurityConfig(
            mode="staging",
            identity_signing_secret_present=True,
            require_tls=False,
            require_authentication=False,
            external_actions_enabled=False,
            automatic_memory_write=False,
        )
        result = config.validate()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("tls_required_for_secure_runtime", result["failures"])
        self.assertIn("authentication_required_for_secure_runtime", result["failures"])

    def test_development_retains_local_bypass_contract(self):
        config = ProductionSecurityConfig.from_env({"AI_OS_RUNTIME_MODE": "development"})
        self.assertFalse(config.require_authentication)
        self.assertFalse(config.require_tls)
        self.assertEqual(config.validate()["status"], "READY")


if __name__ == "__main__":
    unittest.main()
