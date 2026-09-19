from __future__ import annotations

import atexit
import os
import threading
from pathlib import Path

from core.src.auth import build_default_production_authenticator
from unified_runtime.http_api_server import HTTPServerConfig, UnifiedRuntimeHTTPServer
from unified_runtime.security_hardening import ProductionSecurityConfig
from unified_runtime.entrypoint import UnifiedRuntimeEntrypoint

PID_FILE = Path("staging/s21.pid")


def _cleanup() -> None:
    try:
        PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def main() -> None:
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    atexit.register(_cleanup)

    config = ProductionSecurityConfig.from_env()
    authenticator, _identity = build_default_production_authenticator()

    def o36_bearer_adapter(token: str):
        return authenticator.authenticate({"bearer_token": token})

    tls_env = os.getenv("AI_OS_TLS_TERMINATED", "false").lower() == "true"
    entrypoint = UnifiedRuntimeEntrypoint(persistence_root="staging/runs")

    server = UnifiedRuntimeHTTPServer(
        config,
        HTTPServerConfig(
            host=os.getenv("AI_OS_S21_HOST", "127.0.0.1"),
            port=int(os.getenv("AI_OS_S21_PORT", "8091")),
            tls_terminated=tls_env,
        ),
        authenticator=o36_bearer_adapter,
        entrypoint=entrypoint,
    )
    server.start()
    threading.Event().wait()


if __name__ == "__main__":
    main()
