from __future__ import annotations

import os
import unittest

from unified_runtime.security_hardening import (
    SECRET_ENV,
    ProductionSecurityConfig,
    UnifiedRuntimeSecurityHardeningGate,
)


class TestS22_2GateCompatibility(unittest.TestCase):
    def test_explicit_staging_probe_remains_ready_without_real_secret(self):
        env = dict(os.environ)
        env.pop(SECRET_ENV, None)
        env["AI_OS_RUNTIME_MODE"] = "development"
        old = os.environ.get(SECRET_ENV)
        try:
            os.environ.pop(SECRET_ENV, None)
            result = UnifiedRuntimeSecurityHardeningGate(os.getcwd()).run(mode="staging")
        finally:
            if old is None:
                os.environ.pop(SECRET_ENV, None)
            else:
                os.environ[SECRET_ENV] = old
        self.assertEqual(result["status"], "READY_FOR_SECURITY_HARDENING")
        self.assertEqual(result["config"]["mode"], "staging")
        self.assertTrue(result["config"]["require_authentication"])
        self.assertTrue(result["config"]["require_tls"])

    def test_real_staging_config_without_secret_still_blocks(self):
        env = {"AI_OS_RUNTIME_MODE": "staging"}
        config = ProductionSecurityConfig.from_env(env)
        result = config.validate()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("secure_runtime_secret_present", result["failures"])

    def test_explicit_secret_false_still_blocks_staging_gate(self):
        result = UnifiedRuntimeSecurityHardeningGate(os.getcwd()).run(
            mode="staging", secret_present=False
        )
        self.assertEqual(result["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
