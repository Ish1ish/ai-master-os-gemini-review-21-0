import os

from .identity import IdentityProvider, Principal
from .rbac import RBAC


class Authenticator:
    """Authentication hook with an explicit local-development bypass only."""

    def __init__(self, verifier=None, production=False, allow_local_bypass=False):
        self.verifier = verifier
        self.production = bool(production)
        self.allow_local_bypass = bool(allow_local_bypass)

    def __call__(self, bearer_token):
        """Allow the S19/S20 boundary to invoke the authenticator with a token string."""
        return self.authenticate({"bearer_token": bearer_token})

    def authenticate(self, credentials=None):
        if self.verifier is None:
            if self.production:
                return {"status": "UNAUTHENTICATED", "reason": "production_authenticator_not_configured"}
            if self.allow_local_bypass:
                return {
                    "status": "BYPASS_FOR_LOCAL",
                    "principal": "local-dev",
                    "scopes": ["run:submit", "run:read", "run:cancel"],
                }
            return {"status": "UNAUTHENTICATED", "reason": "authenticator_not_configured"}
        result = self.verifier(credentials or {})
        if result.get("status") != "AUTHENTICATED":
            return result
        principal = result.get("principal") or {}
        return {
            "status": "ALLOW",
            "authenticated": True,
            "principal": principal.get("principal_id"),
            "scopes": principal.get("scopes", []),
            "roles": principal.get("roles", []),
            "auth_method": result.get("auth_method", "signed-bearer"),
        }


def build_default_production_authenticator():
    """Create the O36 signed-bearer boundary with server-side principals."""
    identity = IdentityProvider()
    rbac = RBAC()
    for principal_id, principal_type, role in (
        ("viewer-01", "human", "viewer"),
        ("operator-01", "human", "operator"),
        ("approver-01", "human", "approver"),
        ("worker-01", "service", "worker"),
        ("admin-01", "human", "admin"),
    ):
        identity.register(Principal(
            principal_id, principal_type, frozenset({role}),
            frozenset(rbac.scopes_for_roles({role}))
        ))
    return Authenticator(verifier=identity.authenticate, production=True), identity
