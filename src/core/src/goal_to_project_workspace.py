"""Compose goal research, internal plan generation, and persistent workspace creation.

This workflow is a single governed O45 capability. It persists only an
internal draft; it never executes project tasks or performs external business
actions. Search-snippet synthesis remains explicitly non-decision-grade.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping

from .goal_research_workflow import real_goal_research_workflow
from .project_plan_generator import real_project_plan_tool
from .project_workspace_store import ProjectWorkspaceStore, project_workspace_write_tool


def _required_text(value: Any, field: str, limit: int) -> str:
    if not isinstance(value, str):
        raise ValueError("goal_to_workspace_invalid:" + field)
    result = " ".join(value.split())[:limit]
    if not result:
        raise ValueError("goal_to_workspace_required:" + field)
    return result


def real_goal_to_project_workspace(
    payload: Dict[str, Any],
    *,
    store: ProjectWorkspaceStore | None = None,
) -> Dict[str, Any]:
    """Research a goal, create a cited internal plan, then save it as a workspace.

    Required payload: project_id, goal. Optional fields: audience, constraints,
    requested_language, max_queries. The governed runtime supplies requested_by
    from the authenticated principal; callers may not choose another owner.
    """
    if not isinstance(payload, Mapping):
        raise TypeError("goal_to_workspace_payload_must_be_mapping")

    project_id = _required_text(payload.get("project_id"), "project_id", 160)
    goal = _required_text(payload.get("goal"), "goal", 500)
    requested_by = _required_text(payload.get("requested_by"), "requested_by", 160)
    audience = " ".join(str(payload.get("audience") or "").split())[:240]
    language = " ".join(str(payload.get("requested_language") or "en").split())[:40] or "en"
    constraints = payload.get("constraints", {})
    if constraints is None:
        constraints = {}
    if not isinstance(constraints, Mapping):
        raise ValueError("goal_to_workspace_constraints_must_be_mapping")

    research_payload: dict[str, Any] = {
        "goal": goal,
        "audience": audience,
        "constraints": dict(constraints),
        "requested_language": language,
    }
    if "max_queries" in payload:
        research_payload["max_queries"] = payload["max_queries"]

    research = real_goal_research_workflow(research_payload)
    if not isinstance(research, Mapping):
        raise ValueError("goal_to_workspace_research_result_invalid")
    research_status = str(research.get("status") or "").upper()
    if research_status not in {"COMPLETE", "PARTIAL"}:
        raise ValueError("goal_to_workspace_research_status_invalid")

    plan_result = real_project_plan_tool({
        "goal": goal,
        "audience": audience,
        "constraints": dict(constraints),
        "requested_language": language,
        "research": dict(research),
    })
    if not isinstance(plan_result, Mapping):
        raise ValueError("goal_to_workspace_plan_result_invalid")
    if plan_result.get("plan_type") != "INTERNAL_DRAFT" or plan_result.get("decision_grade_evidence") is not False:
        raise ValueError("goal_to_workspace_plan_boundary_invalid")

    saved = project_workspace_write_tool(
        {
            "operation": "create_from_plan",
            "project_id": project_id,
            "requested_by": requested_by,
            "plan_result": dict(plan_result),
        },
        store=store,
    )
    persistence_status = str(saved.get("status") or "UNKNOWN")
    if persistence_status not in {"CREATED", "IDEMPOTENT_REPLAY"}:
        return {
            "provider": "live_goal_to_project_workspace",
            "status": persistence_status,
            "project_id": project_id,
            "workspace_save_status": persistence_status,
            "reason": saved.get("reason", "project_workspace_save_failed"),
            "current_revision": saved.get("current_revision"),
            "workflow_stages": [
                {
                    "stage": "live_market_research",
                    "status": research_status,
                },
                {
                    "stage": "project_plan_draft",
                    "status": str(plan_result.get("status") or "UNKNOWN"),
                },
                {
                    "stage": "persistent_workspace",
                    "status": persistence_status,
                },
            ],
            "decision_grade_evidence": False,
            "external_actions_executed": False,
        }

    stage_rows = research.get("workflow_stages")
    stages = list(stage_rows) if isinstance(stage_rows, list) else []
    stages.append({
        "stage": "project_plan_draft",
        "status": str(plan_result.get("status") or "UNKNOWN"),
    })
    stages.append({
        "stage": "persistent_workspace",
        "status": persistence_status,
        "revision": saved.get("revision"),
    })
    pipeline_status = (
        "PARTIAL"
        if research_status == "PARTIAL"
        or str(plan_result.get("status") or "").upper() == "PARTIAL"
        else "COMPLETE"
    )
    workspace = saved.get("workspace")
    return {
        "provider": "live_goal_to_project_workspace",
        "status": pipeline_status,
        "project_id": project_id,
        "goal": goal,
        "audience": audience,
        "workflow_stages": stages,
        "research": {
            "status": research_status,
            "queries": research.get("research", {}).get("queries", [])
                if isinstance(research.get("research"), Mapping) else [],
            "source_count": len(research.get("sources", []))
                if isinstance(research.get("sources"), list) else 0,
            "synthesis": research.get("synthesis", {}),
        },
        "plan_result": dict(plan_result),
        "sources": list(research.get("sources", []))
            if isinstance(research.get("sources"), list) else [],
        "workspace_save_status": persistence_status,
        "workspace_revision": saved.get("revision"),
        "workspace": workspace,
        "evidence_boundary": research.get(
            "evidence_boundary",
            "DRAFT_PLAN_BASED_ON_UNVERIFIED_SEARCH_SNIPPETS",
        ),
        "decision_grade_evidence": False,
        "external_actions_executed": False,
    }
