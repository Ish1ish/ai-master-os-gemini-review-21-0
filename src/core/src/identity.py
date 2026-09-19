import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import FrozenSet, Dict, Any, Optional

TOKEN_VERSION = "o36.v1"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64url(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


@dataclass(frozen=True)
class Principal:
    principal_id: str
    principal_type: str
    roles: FrozenSet[str]
    scopes: FrozenSet[str]
    active: bool = True

    def to_dict(self):
        return {
            "principal_id": self.principal_id,
            "principal_type": self.principal_type,
            "roles": sorted(self.roles),
            "scopes": sorted(self.scopes),
            "active": self.active,
        }


class IdentityProvider:
    """
    O36 identity registry plus compact HMAC-signed bearer credentials.

    The principal registry remains server-side; bearer tokens contain only a
    principal identifier and bounded lifetime. Production deployments should
    source the signing secret from a secret manager or environment, never
    from source control.
    """

    def __init__(self, signing_secret: Optional[str] = None, token_ttl_seconds: int = 900):
        secret = signing_secret or os.getenv("AI_OS_IDENTITY_SIGNING_SECRET")
        production = os.getenv("AI_OS_ENV", "local").strip().lower() in {"prod", "production"}
        if secret is None:
            if production:
                raise RuntimeError("AI_OS_IDENTITY_SIGNING_SECRET is required in production mode")
            # Explicitly local/dev-only fallback. Never available in production mode.
            secret = "o36-local-development-only-secret"
        if len(secret.encode("utf-8")) < 16:
            raise ValueError("identity signing secret must be at least 16 bytes")
        self._signing_secret = secret.encode("utf-8")
        self.token_ttl_seconds = max(30, int(token_ttl_seconds))
        self._principals: Dict[str, Principal] = {}

    def register(self, principal: Principal):
        self._principals[principal.principal_id] = principal

    def get(self, principal_id: str):
        return self._principals.get(principal_id)

    def _sign(self, payload_segment: str) -> str:
        return _b64url(hmac.new(self._signing_secret, payload_segment.encode("ascii"), hashlib.sha256).digest())

    def issue_token(self, principal_id: str, now: Optional[int] = None) -> Dict[str, Any]:
        principal = self.get(principal_id)
        if not principal or not principal.active:
            return {"status": "DENY", "reason": "principal_inactive_or_unknown"}
        issued = int(time.time() if now is None else now)
        payload = {
            "ver": TOKEN_VERSION,
            "sub": principal.principal_id,
            "iat": issued,
            "exp": issued + self.token_ttl_seconds,
            "jti": os.urandom(16).hex(),
        }
        encoded = _b64url(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        token = f"{encoded}.{self._sign(encoded)}"
        return {"status": "ISSUED", "token": token, "expires_at": payload["exp"], "principal_id": principal.principal_id}

    def authenticate(self, credentials: Dict[str, Any]):
        credentials = credentials or {}
        token = credentials.get("bearer_token") or credentials.get("token")
        if token:
            return self._authenticate_token(token)

        # Legacy principal-id credentials are intentionally disabled by default.
        # Tests/local callers must explicitly opt in through allow_legacy_principal_id.
        if credentials.get("principal_id") and credentials.get("allow_legacy_principal_id") is True:
            principal = self.get(credentials["principal_id"])
            if principal and principal.active:
                return {"status": "AUTHENTICATED", "principal": principal.to_dict(), "auth_method": "legacy-local"}

        return {"status": "UNAUTHENTICATED", "reason": "signed_bearer_token_required"}

    def _authenticate_token(self, token: str):
        try:
            encoded, signature = token.split(".", 1)
            expected = self._sign(encoded)
            if not hmac.compare_digest(signature, expected):
                return {"status": "UNAUTHENTICATED", "reason": "invalid_token_signature"}
            payload = json.loads(_unb64url(encoded).decode("utf-8"))
            if payload.get("ver") != TOKEN_VERSION:
                return {"status": "UNAUTHENTICATED", "reason": "unsupported_token_version"}
            now = int(time.time())
            if int(payload.get("exp", 0)) <= now:
                return {"status": "UNAUTHENTICATED", "reason": "token_expired"}
            if int(payload.get("iat", 0)) > now + 30:
                return {"status": "UNAUTHENTICATED", "reason": "token_not_yet_valid"}
            principal = self.get(str(payload.get("sub", "")))
            if not principal or not principal.active:
                return {"status": "UNAUTHENTICATED", "reason": "principal_inactive_or_unknown"}
            return {"status": "AUTHENTICATED", "principal": principal.to_dict(), "auth_method": "signed-bearer"}
        except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError, KeyError):
            return {"status": "UNAUTHENTICATED", "reason": "malformed_token"}
