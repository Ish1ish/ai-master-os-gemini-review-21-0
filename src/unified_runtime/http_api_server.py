"""S21 real HTTP server/API wiring over the S20 security adapter.

The transport is intentionally standard-library only. The server never performs
external actions or automatic memory writes; every request must pass through the
S20/S19 security boundary before receiving an application response.

TLS is represented as a deployment boundary setting (`tls_terminated`). In a
real deployment this server is expected behind an HTTPS/TLS edge or reverse
proxy that strips/rewrites untrusted forwarding metadata and sets the trusted
termination state. Direct plaintext listeners therefore default to False.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any, Mapping

from .canonical_http_api import CanonicalHTTPAPI
from .http_security_adapter import HTTPProductionSecurityAdapter, HTTPRequest
from .security_hardening import ProductionSecurityConfig


@dataclass(frozen=True)
class HTTPServerConfig:
    host: str = "127.0.0.1"
    port: int = 0
    tls_terminated: bool = False
    request_path: str = "/api/runs"


class _Handler(BaseHTTPRequestHandler):
    server_version = "AIOSUnifiedRuntime/S21"
    sys_version = ""

    def do_POST(self) -> None:  # noqa: N802
        api: "UnifiedRuntimeHTTPServer" = self.server.api_server  # type: ignore[attr-defined]
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw_body.decode("utf-8")) if raw_body else {}
            if not isinstance(body, dict):
                body = {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            body = {}
        response = api.handle_http(
            method="POST",
            path=self.path,
            headers={k: v for k, v in self.headers.items()},
            body=body,
        )
        payload = json.dumps(response.body, sort_keys=True).encode("utf-8")
        self.send_response(response.status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        api: "UnifiedRuntimeHTTPServer" = self.server.api_server  # type: ignore[attr-defined]
        response = api.handle_http(
            method="GET",
            path=self.path,
            headers={k: v for k, v in self.headers.items()},
        )
        payload = json.dumps(response.body, sort_keys=True).encode("utf-8")
        self.send_response(response.status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:
        return


class UnifiedRuntimeHTTPServer:
    VERSION = "1.0"

    def __init__(
        self,
        config: ProductionSecurityConfig,
        server_config: HTTPServerConfig | None = None,
        authenticator=None,
        entrypoint=None,
    ) -> None:
        self.server_config = server_config or HTTPServerConfig()
        self.adapter = HTTPProductionSecurityAdapter(config, authenticator=authenticator)
        self.entrypoint = entrypoint
        self.canonical_api = (
            CanonicalHTTPAPI(entrypoint)
            if entrypoint is not None and hasattr(entrypoint, "runtime")
            else None
        )
        self._server = ThreadingHTTPServer((self.server_config.host, self.server_config.port), _Handler)
        self._server.api_server = self
        self._thread: Thread | None = None

    @property
    def address(self) -> tuple[str, int]:
        return self._server.server_address

    def handle_http(self, *, method: str, path: str, headers: Mapping[str, str], body: Mapping[str, Any] | None = None):
        request = HTTPRequest(
            method=method,
            path=path,
            headers=headers,
            tls_terminated=self.server_config.tls_terminated,
            external_action_requested=bool((body or {}).get("external_action_requested", False)),
            memory_write_requested=bool((body or {}).get("memory_write_requested", False)),
        )
        response = self.adapter.handle(request)
        response.body["http_server_version"] = self.VERSION
        response.body["http_server_io_executed"] = True
        if (
            response.status_code == 200
            and self.canonical_api is not None
            and path.startswith("/api/")
        ):
            principal = response.body.get("authentication", {})
            status_code, app_result = self.canonical_api.handle(
                method=method,
                path=path,
                body=body,
                principal=principal,
            )
            response.status_code = status_code
            response.body["application_response"] = app_result
        elif response.status_code == 200 and self.entrypoint is not None and body is not None:
            principal = response.body.get("authentication", {})
            app_result = self.entrypoint.run(request=body, principal=principal)
            response.body["application_response"] = app_result

        return response

    def start(self) -> tuple[str, int]:
        if self._thread is not None:
            return self.address
        self._thread = Thread(target=self._server.serve_forever, name="aios-s21-http", daemon=True)
        self._thread.start()
        return self.address

    def shutdown(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def __enter__(self) -> "UnifiedRuntimeHTTPServer":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.shutdown()
