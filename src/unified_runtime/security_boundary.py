"""S19/O38 security boundary wiring contract.

This module connects the S18 production security contract to request admission.
It does not expose a server. Production requests fail closed unless an
explicit authenticator is supplied, TLS is asserted by the deployment edge,
and the request carries a non-empty bearer token. External actions and
automatic memory writes remain disabled at this boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .security_hardening import ProductionSecurityConfig

Authenticator = Callable[[str], Mapping[str, Any] | bool]


@dataclass(frozen=True)
class SecurityRequest:
    method: str
    path: str
    bearer_token: str
    tls_terminated: bool
    external_action_requested: bool = False
    memory_write_requested: bool = False


class ProductionSecurityBoundary:
    VERSION = "1.0"

    def __init__(
        self,
        config: ProductionSecurityConfig,
        authenticator: Authenticator | None = None,
    ) -> None:
        self.config = config
        self.authenticator = authenticator

    def _authenticate(self, token: str) -> dict[str, Any]:
        if not self.config.require_authentication:
            return {"status": "BYPASSED_DEVELOPMENT_ONLY", "authenticated": False}
        if self.authenticator is None:
            return {"status": "BLOCKED_NO_AUTHENTICATOR", "authenticated": False}
        try:
            result = self.authenticator(token)
        except Exception as exc:  # fail closed
            return {
                "status": "BLOCKED_AUTHENTICATOR_ERROR",
                "authenticated": False,
                "error_type": type(exc).__name__,
            }
        if result is True:
            return {"status": "AUTHENTICATED", "authenticated": True}
        if isinstance(result, Mapping):
            authenticated = bool(result.get("authenticated", result.get("ok", False)))
            out = dict(result)
            out["authenticated"] = authenticated
            out.setdefault("status", "AUTHENTICATED" if authenticated else "BLOCKED_UNAUTHENTICATED")
            return out
        return {"status": "BLOCKED_UNAUTHENTICATED", "authenticated": False}

    def admit(self, request: SecurityRequest) -> dict[str, Any]:
        config_check = self.config.validate()
        checks = {
            "security_config_ready": config_check["status"] == "READY",
            "path_present": bool(request.path.strip()),
            "method_present": bool(request.method.strip()),
            "tls_ready": (not self.config.require_tls) or bool(request.tls_terminated),
            "token_present": (not self.config.require_authentication) or bool(request.bearer_token.strip()),
            "external_action_blocked": not request.external_action_requested,
            "automatic_memory_write_blocked": not request.memory_write_requested,
        }
        auth = self._authenticate(request.bearer_token)
        checks["authenticated"] = bool(auth.get("authenticated")) if self.config.require_authentication else True
        failures = [k for k, v in checks.items() if not v]
        status = "ADMITTED" if not failures else "BLOCKED"
        return {
            "status": status,
            "boundary": "PRODUCTION_SECURITY_REQUEST_ADMISSION",
            "version": self.VERSION,
            "mode": self.config.mode,
            "checks": checks,
            "failures": failures,
            "authentication": auth,
            "external_action_executed": False,
            "memory_write_executed": False,
            "note": "Request admission only. No network I/O or consequential external action is executed here.",
        }
