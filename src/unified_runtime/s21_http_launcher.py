from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from core.src.auth import build_default_production_authenticator
from core.src.canonical_provider_tools import real_research_tool, real_search_tool
from core.src.research_synthesis import real_research_synthesis_tool
from core.src.goal_research_workflow import real_goal_research_workflow
from core.src.project_plan_generator import real_project_plan_tool
from core.src.goal_to_project_workspace import real_goal_to_project_workspace
from core.src.project_progress_review import project_progress_review_tool
from core.src.project_workspace_store import (
    ProjectWorkspaceStore,
    project_workspace_read_tool,
    project_workspace_write_tool,
)

from .entrypoint import UnifiedRuntimeEntrypoint
from .http_api_server import HTTPServerConfig, UnifiedRuntimeHTTPServer
from .security_hardening import ProductionSecurityConfig


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8091
DEFAULT_PERSISTENCE_ROOT = "./staging/s21_http_runtime"
TLS_EDGE_ENV = "AI_OS_TLS_TERMINATED_BY_EDGE"
MODE_ENV = "AI_OS_RUNTIME_MODE"
PORT_ENV = "AI_OS_S21_PORT"
HOST_ENV = "AI_OS_S21_HOST"
PERSISTENCE_ENV = "AI_OS_UNIFIED_RUNTIME_PERSISTENCE_ROOT"


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def build_s21_http_server(
    *,
    host: str | None = None,
    port: int | None = None,
    tls_terminated: bool | None = None,
    persistence_root: str | Path | None = None,
):
    """Compose the canonical S21 HTTP boundary without creating a new authority.

    The returned tuple is (server, entrypoint, identity_provider). Callers own
    shutdown/close lifecycle. External actions remain disabled by the entrypoint.
    """
    config = ProductionSecurityConfig.from_env()
    validation = config.validate()
    if validation["status"] != "READY":
        failures = ",".join(validation["failures"]) or "security_configuration_invalid"
        raise RuntimeError(f"s21_security_config_blocked:{failures}")

    authenticator, identity = build_default_production_authenticator()
    worker_principal_id = os.getenv(
        "AI_OS_EXECUTION_WORKER_PRINCIPAL_ID",
        "worker-01",
    ).strip()
    worker_principal = identity.get(worker_principal_id)
    if not worker_principal or not worker_principal.active:
        raise RuntimeError(f"s21_execution_worker_invalid:{worker_principal_id}")
    worker_dict = worker_principal.to_dict()
    if worker_dict.get("principal_type") != "service":
        raise RuntimeError(f"s21_execution_worker_not_service:{worker_principal_id}")
    if "job:execute" not in set(worker_dict.get("scopes") or []):
        raise RuntimeError(
            f"s21_execution_worker_missing_job_execute:{worker_principal_id}"
        )
    execution_principal = {
        "status": "AUTHENTICATED",
        "authenticated": True,
        "principal": worker_dict["principal_id"],
        "principal_id": worker_dict["principal_id"],
        "scopes": list(worker_dict.get("scopes") or []),
        "roles": list(worker_dict.get("roles") or []),
        "auth_method": "internal-worker",
    }
    root = Path(
        persistence_root
        or os.getenv(PERSISTENCE_ENV, DEFAULT_PERSISTENCE_ROOT)
    ).resolve()
    entrypoint = UnifiedRuntimeEntrypoint(str(root), enable_external_actions=False)
    entrypoint.register_execution_tool(
        "provider.search.live", real_search_tool, version="1.0.0", retry_safe=False
    )
    entrypoint.register_execution_tool(
        "provider.research.live", real_research_tool, version="1.0.0", retry_safe=False
    )
    entrypoint.register_execution_tool(
        "provider.research.synthesis",
        real_research_synthesis_tool,
        version="1.0.0",
        retry_safe=False,
    )
    entrypoint.register_execution_tool(
        "provider.research.workflow",
        real_goal_research_workflow,
        version="1.0.0",
        retry_safe=False,
    )
    entrypoint.register_execution_tool(
        "provider.project.plan",
        real_project_plan_tool,
        version="1.0.0",
        retry_safe=False,
    )
    workspace_store = ProjectWorkspaceStore(root / "project_workspace.sqlite3")
    entrypoint.register_execution_tool(
        "provider.project.workspace.read",
        lambda payload: project_workspace_read_tool(payload, store=workspace_store),
        version="1.0.0",
        retry_safe=True,
    )
    entrypoint.register_execution_tool(
        "provider.project.workspace.review",
        lambda payload: project_progress_review_tool(payload, store=workspace_store),
        version="1.0.0",
        retry_safe=True,
    )
    entrypoint.register_execution_tool(
        "provider.project.workspace.write",
        lambda payload: project_workspace_write_tool(payload, store=workspace_store),
        version="1.0.0",
        retry_safe=False,
    )
    entrypoint.register_execution_tool(
        "provider.project.goal-to-workspace",
        lambda payload: real_goal_to_project_workspace(payload, store=workspace_store),
        version="1.0.0",
        retry_safe=False,
    )
    entrypoint.execution_principal = execution_principal

    server_config = HTTPServerConfig(
        host=host or os.getenv(HOST_ENV, DEFAULT_HOST),
        port=(port if port is not None else int(os.getenv(PORT_ENV, str(DEFAULT_PORT)))),
        tls_terminated=(
            tls_terminated
            if tls_terminated is not None
            else _env_bool(TLS_EDGE_ENV, False)
        ),
        request_path="/api/runs",
    )

    server = UnifiedRuntimeHTTPServer(
        config,
        server_config,
        authenticator=lambda token: authenticator.authenticate({"bearer_token": token}),
        entrypoint=entrypoint,
    )
    return server, entrypoint, identity


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AI Master OS canonical S21 HTTP server")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--persistence-root", default=None)
    parser.add_argument("--tls-terminated", action="store_true")
    args = parser.parse_args(argv)

    server, entrypoint, _identity = build_s21_http_server(
        host=args.host,
        port=args.port,
        persistence_root=args.persistence_root,
        tls_terminated=(True if args.tls_terminated else None),
    )
    host, port = server.address
    try:
        server.start()
        print(f"AI Master OS S21 HTTP listening on http://{host}:{port}")
        print("canonical surface: /api/runs /api/intents/{intent_id}/execute /api/approvals /api/executions/{execution_id} /api/experiments /api/learning/context")
        print("external actions: disabled")
        print("automatic memory write: disabled")
        server._thread.join()
    except KeyboardInterrupt:
        return 0
    finally:
        server.shutdown()
        entrypoint.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
