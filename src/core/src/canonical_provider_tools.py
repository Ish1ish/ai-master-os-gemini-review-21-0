"""Canonical O45 tool adapters over the real live provider clients.

These wrappers exist solely to translate the O45 ExecutionService's single
positional payload-dict handler contract (see tool_registry.ToolHandler) into
the live_providers module's existing prompt/query-based real HTTP provider
calls. They perform no governance and no credential handling themselves -
live_providers reads provider credentials directly from the environment
(AI_OS_MODEL_API_KEY / AI_OS_SEARCH_API_KEY) and this module never touches,
logs, or returns them.

Only a read-only/advisory provider operation (search) is wired here for the
first real-provider governed-execution milestone, per the safety boundary:
no irreversible external business side effect is performed by these tools.
"""
from __future__ import annotations

from typing import Any, Dict

from .live_providers import search_provider


def real_search_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
    """O45 tool handler: real, read-only search provider call.

    Payload contract: {"query": <non-empty string>}.
    Returns a normalized, credential-free result. Any provider failure
    (missing configuration, HTTP error, timeout, malformed response) raises
    from live_providers.search_provider and is caught by
    o45_execution_service.ExecutionService.execute_once, which converts it
    into a governed FAILED_RETRYABLE / RECOVERY_REQUIRED outcome rather than
    an uncaught crash. This function does not add its own try/except so that
    ExecutionService remains the single place execution failures are
    classified.
    """
    query = str((payload or {}).get("query") or "").strip()
    if not query:
        raise ValueError("query_required")
    result = search_provider(query)
    rows = result.get("results", [])
    return {
        "provider": "live_search",
        "query": query,
        "result_count": len(rows),
        "results": rows,
    }
