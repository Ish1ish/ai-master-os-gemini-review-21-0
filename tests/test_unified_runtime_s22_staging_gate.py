from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from unified_runtime.security_hardening import SECRET_ENV
from unified_runtime.staging_gate import (
    OPENROUTER_ENV,
    STAGING_BASE_URL_ENV,
    TAVILY_ENV,
    TLS_EDGE_ENV,
    DIRECT_EXPOSURE_ENV,
    O38StagingGoLiveGate,
    StagingBackupManager,
    StagingEnvironmentContract,
    scrubbed_environment,
)


class TestS22StagingGate(unittest.TestCase):
    def _base_env(self):
        return {
            "AI_OS_RUNTIME_MODE": "staging",
            SECRET_ENV: "test-secret",
            STAGING_BASE_URL_ENV: "https://staging.example.test",
            TLS_EDGE_ENV: "true",
            DIRECT_EXPOSURE_ENV: "false",
        }

    def test_complete_staging_contract_is_ready_without_live_provider_requirement(self):
        result = StagingEnvironmentContract.from_env(self._base_env()).validate()
        self.assertEqual(result["status"], "READY")
        self.assertFalse(result["provider_credentials_verified"])

    def test_missing_identity_secret_blocks(self):
        env = self._base_env()
        env.pop(SECRET_ENV)
        result = StagingEnvironmentContract.from_env(env).validate()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("identity_secret_present", result["failures"])

    def test_missing_tls_edge_blocks(self):
        env = self._base_env()
        env[TLS_EDGE_ENV] = "false"
        result = StagingEnvironmentContract.from_env(env).validate()
        self.assertIn("tls_edge_enabled", result["failures"])

    def test_direct_exposure_blocks(self):
        env = self._base_env()
        env[DIRECT_EXPOSURE_ENV] = "true"
        result = StagingEnvironmentContract.from_env(env).validate()
        self.assertIn("direct_service_exposure_disabled", result["failures"])

    def test_live_provider_requirement_blocks_without_keys(self):
        result = StagingEnvironmentContract.from_env(self._base_env()).validate(require_live_providers=True)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("tavily_api_key_present", result["failures"])
        self.assertIn("openrouter_api_key_present", result["failures"])

    def test_live_provider_requirement_accepts_presence_only(self):
        env = self._base_env()
        env[TAVILY_ENV] = "tavily-secret"
        env[OPENROUTER_ENV] = "openrouter-secret"
        result = StagingEnvironmentContract.from_env(env).validate(require_live_providers=True)
        self.assertEqual(result["status"], "READY")
        self.assertFalse(result["provider_credentials_verified"])

    def test_backup_restore_roundtrip(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            source = root_path / "source"
            backup = root_path / "backup"
            restored = root_path / "restored"
            source.mkdir()
            (source / "state.json").write_text('{"version":1}', encoding="utf-8")
            manager = StagingBackupManager()
            snap = manager.snapshot(source, backup)
            self.assertEqual(snap["status"], "READY")
            result = manager.restore(backup, restored)
            self.assertEqual(result["status"], "READY")
            self.assertEqual((restored / "state.json").read_text(encoding="utf-8"), '{"version":1}')

    def test_go_live_gate_stays_blocked_without_runtime_evidence(self):
        result = O38StagingGoLiveGate().evaluate(self._base_env())
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("backup_restore_verified", result["failures"])
        self.assertIn("target_http_smoke_verified", result["failures"])

    def test_go_live_gate_can_be_ready_with_explicit_acceptance_evidence(self):
        result = O38StagingGoLiveGate().evaluate(
            self._base_env(),
            require_live_providers=True,
            backup_restore_verified=True,
            target_http_smoke_verified=True,
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("tavily_api_key_present", result["failures"])

    def test_secret_values_are_redacted(self):
        env = self._base_env() | {TAVILY_ENV: "abc", OPENROUTER_ENV: "xyz"}
        scrubbed = scrubbed_environment(env)
        self.assertEqual(scrubbed[SECRET_ENV], "<present>")
        self.assertEqual(scrubbed[TAVILY_ENV], "<present>")
        self.assertEqual(scrubbed[OPENROUTER_ENV], "<present>")
        self.assertNotIn("abc", scrubbed.values())
        self.assertNotIn("xyz", scrubbed.values())


if __name__ == "__main__":
    unittest.main()
