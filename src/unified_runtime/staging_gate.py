"""O38 staging environment and go-live gate.

This module makes the remaining O38 deployment conditions explicit without
pretending that the model/search providers or target infrastructure have been
verified. Real provider credentials are consumed only from the environment and
are never returned in gate output.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .security_hardening import SECRET_ENV


TAVILY_ENV = "TAVILY_API_KEY"
OPENROUTER_ENV = "OPENROUTER_API_KEY"
MODE_ENV = "AI_OS_RUNTIME_MODE"
STAGING_BASE_URL_ENV = "AI_OS_STAGING_BASE_URL"
TLS_EDGE_ENV = "AI_OS_TLS_TERMINATED_BY_EDGE"
DIRECT_EXPOSURE_ENV = "AI_OS_DIRECT_SERVICE_EXPOSURE"


@dataclass(frozen=True)
class StagingEnvironmentContract:
    mode: str
    identity_secret_present: bool
    tavily_key_present: bool
    openrouter_key_present: bool
    staging_base_url_present: bool
    tls_edge_enabled: bool
    direct_service_exposure_disabled: bool

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "StagingEnvironmentContract":
        values = os.environ if env is None else env
        mode = str(values.get(MODE_ENV, "")).strip().lower()
        return cls(
            mode=mode,
            identity_secret_present=bool(str(values.get(SECRET_ENV, "")).strip()),
            tavily_key_present=bool(str(values.get(TAVILY_ENV, "")).strip()),
            openrouter_key_present=bool(str(values.get(OPENROUTER_ENV, "")).strip()),
            staging_base_url_present=bool(str(values.get(STAGING_BASE_URL_ENV, "")).strip()),
            tls_edge_enabled=str(values.get(TLS_EDGE_ENV, "")).strip().lower() == "true",
            direct_service_exposure_disabled=str(values.get(DIRECT_EXPOSURE_ENV, "true")).strip().lower() == "false",
        )

    def validate(self, *, require_live_providers: bool = False) -> dict[str, Any]:
        checks = {
            "staging_or_production_mode": self.mode in {"staging", "stage", "production", "prod"},
            "identity_secret_present": self.identity_secret_present,
            "staging_base_url_present": self.staging_base_url_present,
            "tls_edge_enabled": self.tls_edge_enabled,
            "direct_service_exposure_disabled": self.direct_service_exposure_disabled,
        }
        if require_live_providers:
            checks["tavily_api_key_present"] = self.tavily_key_present
            checks["openrouter_api_key_present"] = self.openrouter_key_present
        failures = [name for name, ok in checks.items() if not ok]
        return {
            "status": "READY" if not failures else "BLOCKED",
            "checks": checks,
            "failures": failures,
            "provider_credentials_verified": False,
            "note": "Environment contract only; presence of provider secrets is not evidence of provider authentication or successful live calls.",
        }


class StagingBackupManager:
    """Small deterministic file-level backup/restore primitive for staging artifacts."""

    VERSION = "1.0"

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def snapshot(self, source_dir: str | Path, backup_dir: str | Path) -> dict[str, Any]:
        source = Path(source_dir)
        backup = Path(backup_dir)
        if not source.is_dir():
            return {"status": "BLOCKED", "reason": "source_dir_missing"}
        backup.mkdir(parents=True, exist_ok=True)
        target = backup / "snapshot"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
        manifest: dict[str, str] = {}
        for path in sorted(target.rglob("*")):
            if path.is_file():
                manifest[str(path.relative_to(target))] = self._hash_file(path)
        (backup / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        return {"status": "READY", "file_count": len(manifest), "manifest_sha256": self._hash_file(backup / "manifest.json")}

    def restore(self, backup_dir: str | Path, target_dir: str | Path) -> dict[str, Any]:
        backup = Path(backup_dir)
        target = Path(target_dir)
        snapshot = backup / "snapshot"
        if not snapshot.is_dir():
            return {"status": "BLOCKED", "reason": "snapshot_missing"}
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(snapshot, target)
        return {"status": "READY", "restored": True}


class O38StagingGoLiveGate:
    VERSION = "1.0"

    def evaluate(
        self,
        env: Mapping[str, str] | None = None,
        *,
        require_live_providers: bool = False,
        backup_restore_verified: bool = False,
        target_http_smoke_verified: bool = False,
    ) -> dict[str, Any]:
        contract = StagingEnvironmentContract.from_env(env)
        validation = contract.validate(require_live_providers=require_live_providers)
        checks = {
            "environment_contract_ready": validation["status"] == "READY",
            "backup_restore_verified": bool(backup_restore_verified),
            "target_http_smoke_verified": bool(target_http_smoke_verified),
            "live_provider_smoke_verified": bool(require_live_providers and contract.tavily_key_present and contract.openrouter_key_present and target_http_smoke_verified),
        }
        failures = list(validation["failures"])
        failures.extend(name for name, ok in checks.items() if not ok)
        deduped_failures = list(dict.fromkeys(failures))
        ready = not deduped_failures
        return {
            "status": "READY" if ready else "BLOCKED",
            "gate": "O38_STAGING_GO_LIVE_ACCEPTANCE",
            "version": self.VERSION,
            "checks": {**validation["checks"], **checks},
            "failures": deduped_failures,
            "provider_credentials_verified": False,
            "external_action_executed": False,
            "automatic_memory_write": False,
            "note": "READY is valid only for the supplied acceptance evidence; provider credentials are never echoed and live calls are not performed by this gate.",
        }


def scrubbed_environment(env: Mapping[str, str]) -> dict[str, str]:
    """Return a safe environment view with secret values redacted."""
    secret_names = {SECRET_ENV, TAVILY_ENV, OPENROUTER_ENV}
    return {key: ("<present>" if key in secret_names and str(value).strip() else "<missing>" if key in secret_names else str(value)) for key, value in env.items()}
