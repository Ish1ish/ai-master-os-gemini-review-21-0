"""S20 HTTP/API security adapter.

Translates HTTP-like request metadata into the authoritative S19 security
boundary and maps admission results to deterministic HTTP responses.
No socket, server, or external I/O is opened here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .security_boundary import ProductionSecurityBoundary, SecurityRequest
from .security_hardening import ProductionSecurityConfig

Authenticator = Callable[[str], Mapping[str, Any] | bool]


@dataclass(frozen=True)
class HTTPRequest:
    method: str
    path: str
    headers: Mapping[str, str]
    tls_terminated: bool
    external_action_requested: bool = False
    memory_write_requested: bool = False


class HTTPResponse:
    def __init__(self, status_code: int, body: dict[str, Any]):
        self.status_code = status_code
        self.body = body

    def as_dict(self) -> dict[str, Any]:
        return {"status_code": self.status_code, "body": self.body}


class HTTPProductionSecurityAdapter:
    VERSION = "1.0"

    def __init__(
        self,
        config: ProductionSecurityConfig,
        authenticator: Authenticator | None = None,
    ) -> None:
        self.boundary = ProductionSecurityBoundary(config, authenticator=authenticator)

    @staticmethod
    def _bearer(headers: Mapping[str, str]) -> str:
        raw = ""
        for key, value in headers.items():
            if key.lower() == "authorization":
                raw = str(value).strip()
                break
        if not raw:
            return ""
        scheme, sep, token = raw.partition(" ")
        if sep and scheme.lower() == "bearer":
            return token.strip()
        return ""

    def handle(self, request: HTTPRequest) -> HTTPResponse:
        token = self._bearer(request.headers)
        result = self.boundary.admit(
            SecurityRequest(
                method=request.method,
                path=request.path,
                bearer_token=token,
                tls_terminated=request.tls_terminated,
                external_action_requested=request.external_action_requested,
                memory_write_requested=request.memory_write_requested,
            )
        )
        if result["status"] == "ADMITTED":
            status_code = 200
        elif "authenticated" in result["failures"] or "token_present" in result["failures"]:
            status_code = 401
        else:
            status_code = 403
        result["http_adapter_version"] = self.VERSION
        result["http_io_executed"] = False
        return HTTPResponse(status_code, result)
