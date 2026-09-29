from __future__ import annotations

import atexit
import os
import threading
from pathlib import Path

from unified_runtime.s21_http_launcher import build_s21_http_server

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

    tls_env = os.getenv("AI_OS_TLS_TERMINATED", "false").lower() == "true"
    server, entrypoint, _identity = build_s21_http_server(
        host=os.getenv("AI_OS_S21_HOST", "127.0.0.1"),
        port=int(os.getenv("AI_OS_S21_PORT", "8091")),
        tls_terminated=tls_env,
        persistence_root=os.getenv("AI_OS_UNIFIED_RUNTIME_PERSISTENCE_ROOT", "staging/runs"),
    )
    try:
        server.start()
        threading.Event().wait()
    finally:
        server.shutdown()
        entrypoint.close()


if __name__ == "__main__":
    main()
