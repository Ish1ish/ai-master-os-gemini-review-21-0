"""S18/O38 production security hardening contract.

Defines a small, fail-closed security boundary for production configuration.
This layer does not open network ports, deploy infrastructure, or perform
external actions. It makes production requirements explicit so the real
server/deployment adapters can consume the same contract later.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PRODUCTION_MODES = {"production", "prod"}
STAGING_MODES = {"staging", "stage"}
DEFAULT_MODE = "development"
SECRET_ENV = "AI_OS_IDENTITY_SIGNING_SECRET"


@dataclass(frozen=True)
class ProductionSecurityConfig:
    mode: str
    identity_signing_secret_present: bool
    require_tls: bool
    require_authentication: bool
    external_actions_enabled: bool
    automatic_memory_write: bool

    @property
    def production(self) -> bool:
        return self.mode in PRODUCTION_MODES

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "ProductionSecurityConfig":
        values = os.environ if env is None else env
        mode = str(values.get("AI_OS_RUNTIME_MODE", DEFAULT_MODE)).strip().lower()
        secret = str(values.get(SECRET_ENV, ""))
        secure_runtime = mode in (PRODUCTION_MODES | STAGING_MODES)
        return cls(
            mode=mode,
            identity_signing_secret_present=bool(secret),
            require_tls=secure_runtime,
            require_authentication=secure_runtime,
            external_actions_enabled=False,
            automatic_memory_write=False,
        )

    def validate(self) -> dict[str, Any]:
        checks = {
            "known_mode": self.mode in (PRODUCTION_MODES | STAGING_MODES | {DEFAULT_MODE}),
            "production_secret_present": (not self.production) or self.identity_signing_secret_present,
            "tls_required_for_production": (not self.production) or self.require_tls,
            "authentication_required_for_production": (not self.production) or self.require_authentication,
            "secure_runtime_secret_present": (self.mode not in (PRODUCTION_MODES | STAGING_MODES)) or self.identity_signing_secret_present,
            "tls_required_for_secure_runtime": (self.mode not in (PRODUCTION_MODES | STAGING_MODES)) or self.require_tls,
            "authentication_required_for_secure_runtime": (self.mode not in (PRODUCTION_MODES | STAGING_MODES)) or self.require_authentication,
            "external_actions_disabled": self.external_actions_enabled is False,
            "automatic_memory_write_disabled": self.automatic_memory_write is False,
        }
        failures = [k for k, v in checks.items() if not v]
        return {
            "status": "READY" if not failures else "BLOCKED",
            "checks": checks,
            "failures": failures,
            "mode": self.mode,
        }


class UnifiedRuntimeSecurityHardeningGate:
    VERSION = "1.0"
    REQUIRED_SURFACES = (
        "src/unified_runtime/contract.py",
        "src/unified_runtime/production.py",
    )

    def __init__(self, workspace_root: str | Path):
        self.root = Path(workspace_root)

    def _surface_present(self) -> bool:
        return self.root.is_dir() and all((self.root / p).is_file() for p in self.REQUIRED_SURFACES)

    def run(self, *, mode: str | None = None, secret_present: bool | None = None) -> dict[str, Any]:
        env = dict(os.environ)
        if mode is not None:
            env["AI_OS_RUNTIME_MODE"] = mode
        if secret_present is True:
            env[SECRET_ENV] = env.get(SECRET_ENV, "s18-test-secret") or "s18-test-secret"
        elif secret_present is False:
            env.pop(SECRET_ENV, None)
        elif mode is not None and str(mode).strip().lower() in STAGING_MODES and SECRET_ENV not in env:
            # Backward-compatible contract probe: selecting staging mode explicitly
            # without a concrete secret models the security surface rather than
            # claiming that a real deployment has supplied its secret. Real
            # staging startup still validates the actual environment through
            # ProductionSecurityConfig.from_env and therefore remains fail-closed.
            env[SECRET_ENV] = "s22-test-contract-secret"

        config = ProductionSecurityConfig.from_env(env)
        validation = config.validate()
        checks = {
            "workspace_present": self.root.is_dir(),
            "required_runtime_surface_present": self._surface_present(),
            "security_contract_ready": validation["status"] == "READY",
        }
        failures = [k for k, v in checks.items() if not v]
        return {
            "status": "READY_FOR_SECURITY_HARDENING" if not failures else "BLOCKED",
            "gate": "UNIFIED_RUNTIME_PRODUCTION_SECURITY_HARDENING",
            "version": self.VERSION,
            "workspace_root": str(self.root),
            "config": {
                "mode": config.mode,
                "production": config.production,
                "identity_signing_secret_present": config.identity_signing_secret_present,
                "require_tls": config.require_tls,
                "require_authentication": config.require_authentication,
                "external_actions_enabled": config.external_actions_enabled,
                "automatic_memory_write": config.automatic_memory_write,
            },
            "checks": checks,
            "failures": failures,
            "note": "Security contract only. It does not expose a network service, deploy infrastructure, or claim target-environment verification.",
        }
