"""One-goal read-only workflow: live search followed by source-grounded synthesis.

This is a composite O45 tool for the user-facing goal-to-research path. It
keeps search and model interpretation as distinct stages in the returned
trace, preserves source provenance, and never converts synthesis into
decision-grade evidence.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping

from .canonical_provider_tools import _clean_text, real_research_tool
from .research_synthesis import real_research_synthesis_tool


def real_goal_research_workflow(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Collect goal-aware market sources and synthesize them in one governed run.

    Payload accepts goal, optional audience, constraints, requested_language,
    max_queries. At most six provider search queries are delegated to the
    bounded PATCH18 research tool, followed by one model synthesis call.
    """
    if not isinstance(payload, Mapping):
        raise TypeError("goal_research_payload_must_be_mapping")
    goal = _clean_text(payload.get("goal"), limit=500)
    if not goal:
        raise ValueError("goal_required")
    audience = _clean_text(payload.get("audience"), limit=240)
    requested_language = _clean_text(payload.get("requested_language") or "en", limit=40)
    constraints = payload.get("constraints", {})
    if constraints is None:
        constraints = {}
    if not isinstance(constraints, Mapping):
        raise ValueError("constraints_must_be_mapping")

    research_payload: dict[str, Any] = {
        "goal": goal,
        "audience": audience,
        "constraints": dict(constraints),
    }
    if "max_queries" in payload:
        research_payload["max_queries"] = payload["max_queries"]

    # Search and synthesis stay visible as separate stages, but the caller
    # needs only one explicit, governed O45 execution to run the workflow.
    research = real_research_tool(research_payload)
    synthesis = real_research_synthesis_tool({
        "goal": goal,
        "audience": audience,
        "requested_language": requested_language,
        "results": research["results"],
    })

    overall_status = (
        "PARTIAL"
        if research.get("status") != "COMPLETE"
        else "COMPLETE"
    )
    return {
        "provider": "live_goal_research_workflow",
        "status": overall_status,
        "goal": goal,
        "audience": audience,
        "requested_language": requested_language,
        "workflow_stages": [
            {
                "stage": "live_market_research",
                "status": research.get("status", "UNKNOWN"),
                "query_count": research.get("query_count", 0),
                "source_count": research.get("result_count", 0),
            },
            {
                "stage": "source_grounded_synthesis",
                "status": synthesis.get("status", "UNKNOWN"),
                "source_count": synthesis.get("source_count", 0),
            },
        ],
        "research": {
            "queries": research.get("queries", []),
            "query_count": research.get("query_count", 0),
            "query_statuses": research.get("query_statuses", []),
            "result_count": research.get("result_count", 0),
        },
        "sources": synthesis.get("sources", []),
        "synthesis": synthesis.get("synthesis", {}),
        "evidence_boundary": synthesis.get(
            "evidence_boundary",
            "SYNTHESIS_OF_SUPPLIED_SEARCH_SNIPPETS_NOT_FULL_PAGE_VERIFICATION",
        ),
        "decision_grade_evidence": False,
    }
