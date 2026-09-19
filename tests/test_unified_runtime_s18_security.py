from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from unified_runtime.security_hardening import (
    ProductionSecurityConfig,
    SECRET_ENV,
    UnifiedRuntimeSecurityHardeningGate,
)


class TestS18ProductionSecurityHardening(unittest.TestCase):
    def _workspace(self) -> Path:
        root = Path(tempfile.mkdtemp())
        (root / "src" / "unified_runtime").mkdir(parents=True)
        (root / "src" / "unified_runtime" / "contract.py").write_text("# contract\n", encoding="utf-8")
        (root / "src" / "unified_runtime" / "production.py").write_text("# production\n", encoding="utf-8")
        return root

    def test_development_mode_does_not_require_secret(self):
        result = ProductionSecurityConfig.from_env({"AI_OS_RUNTIME_MODE": "development"}).validate()
        self.assertEqual(result["status"], "READY")

    def test_staging_mode_is_supported_but_secure_without_secret_is_blocked(self):
        result = ProductionSecurityConfig.from_env({"AI_OS_RUNTIME_MODE": "staging"}).validate()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("secure_runtime_secret_present", result["failures"])

    def test_production_requires_secret(self):
        result = ProductionSecurityConfig.from_env({"AI_OS_RUNTIME_MODE": "production"}).validate()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("production_secret_present", result["failures"])

    def test_production_with_secret_is_ready(self):
        result = ProductionSecurityConfig.from_env({
            "AI_OS_RUNTIME_MODE": "production",
            SECRET_ENV: "test-secret",
        }).validate()
        self.assertEqual(result["status"], "READY")

    def test_unknown_mode_fails_closed(self):
        result = ProductionSecurityConfig.from_env({"AI_OS_RUNTIME_MODE": "unknown"}).validate()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("known_mode", result["failures"])

    def test_external_actions_are_always_disabled(self):
        config = ProductionSecurityConfig.from_env({"AI_OS_RUNTIME_MODE": "production", SECRET_ENV: "s"})
        self.assertFalse(config.external_actions_enabled)

    def test_automatic_memory_write_is_always_disabled(self):
        config = ProductionSecurityConfig.from_env({"AI_OS_RUNTIME_MODE": "production", SECRET_ENV: "s"})
        self.assertFalse(config.automatic_memory_write)

    def test_gate_passes_for_contract_ready_workspace(self):
        gate = UnifiedRuntimeSecurityHardeningGate(self._workspace())
        result = gate.run(mode="production", secret_present=True)
        self.assertEqual(result["status"], "READY_FOR_SECURITY_HARDENING")
        self.assertTrue(result["checks"]["required_runtime_surface_present"])

    def test_gate_blocks_missing_workspace(self):
        root = Path(tempfile.mkdtemp()) / "missing"
        result = UnifiedRuntimeSecurityHardeningGate(root).run(mode="production", secret_present=True)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("workspace_present", result["failures"])

    def test_gate_blocks_missing_production_secret(self):
        gate = UnifiedRuntimeSecurityHardeningGate(self._workspace())
        result = gate.run(mode="production", secret_present=False)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("security_contract_ready", result["failures"])


if __name__ == "__main__":
    unittest.main()
