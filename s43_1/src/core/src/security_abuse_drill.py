from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Principal:
    subject: str
    roles: tuple[str, ...]
    scopes: tuple[str, ...]
    tenant_id: str


def authorize(principal: Principal, required_scope: str, tenant_id: str, owner_tenant_id: str) -> bool:
    if principal.tenant_id != tenant_id:
        return False
    if principal.tenant_id != owner_tenant_id:
        return False
    return required_scope in principal.scopes or "admin:*" in principal.scopes


def replay_guard(seen: set[str], request_id: str) -> bool:
    if request_id in seen:
        return False
    seen.add(request_id)
    return True


def fail_closed_token(token: str | None) -> bool:
    return bool(token) and token.startswith("signed.")


def run_security_abuse_drill() -> dict:
    operator = Principal("operator-01", ("operator",), ("run:submit", "run:execute"), "tenant-A")
    attacker = Principal("attacker-01", ("viewer",), ("read:only",), "tenant-B")
    seen: set[str] = set()

    checks = {
        "missing_token_rejected": not fail_closed_token(None),
        "malformed_token_rejected": not fail_closed_token("garbage"),
        "scope_escalation_denied": not authorize(operator, "admin:delete", "tenant-A", "tenant-A"),
        "cross_tenant_access_denied": not authorize(attacker, "run:execute", "tenant-A", "tenant-A"),
        "tenant_owner_mismatch_denied": not authorize(operator, "run:execute", "tenant-A", "tenant-B"),
        "replay_request_blocked": replay_guard(seen, "req-001") and not replay_guard(seen, "req-001"),
        "valid_scoped_access_allowed": authorize(operator, "run:execute", "tenant-A", "tenant-A"),
        "admin_scope_override_explicit": authorize(
            Principal("admin-01", ("admin",), ("admin:*",), "tenant-A"),
            "admin:delete", "tenant-A", "tenant-A"
        ),
    }
    checks["adversarial_drill_pass"] = all(checks.values())
    return checks
