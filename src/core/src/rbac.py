from typing import Dict, Set


DEFAULT_ROLE_SCOPES: Dict[str, Set[str]] = {
    "viewer": {"run:read", "approval:read", "control:read"},
    "operator": {
        "run:submit", "run:read", "run:list", "run:execute", "run:cancel", "run:retry", "control:read",
        "governance:read", "governance:evaluate",
        "queue:recover", "dlq:replay", "approval:read",
    },
    "approver": {
        "run:read", "approval:read", "approval:decide", "control:read", "governance:read",
    },
    "worker": {
        "run:read", "job:execute", "memory:write", "audit:write",
    },
    "validator": {
        "experiment:read", "experiment:write", "experiment:evaluate", "learning:read",
    },
    "admin": {
        "run:submit", "run:read", "run:list", "run:execute", "run:cancel", "run:retry", "control:read",
        "queue:recover", "dlq:replay", "approval:read", "approval:decide", "governance:read", "governance:evaluate",
        "policy:manage", "identity:manage", "tenant:cross",
    },
}


class RBAC:
    def __init__(self, role_scopes=None):
        self.role_scopes = dict(role_scopes or DEFAULT_ROLE_SCOPES)

    def scopes_for_roles(self, roles):
        scopes = set()
        for role in roles:
            scopes.update(self.role_scopes.get(role, set()))
        return scopes

    def authorize(self, principal, required_scope: str):
        if not principal:
            return {"status": "UNAUTHENTICATED", "required_scope": required_scope}
        if not principal.get("active", False):
            return {"status": "DENY", "reason": "principal_inactive"}
        if required_scope in principal.get("scopes", []):
            return {"status": "ALLOW", "required_scope": required_scope}
        role_scopes = self.scopes_for_roles(principal.get("roles", []))
        if required_scope in role_scopes:
            return {"status": "ALLOW", "required_scope": required_scope}
        return {"status": "DENY", "reason": "scope_not_granted", "required_scope": required_scope}
