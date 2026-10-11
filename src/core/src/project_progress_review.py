"""Deterministic, read-only progress review for a persistent project workspace.

This module reports existing task and milestone state. It does not call a model,
change the workspace, execute tasks, or perform external business actions.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping

from .project_workspace_store import ProjectWorkspaceStore, project_workspace_read_tool


def project_progress_review_tool(
    payload: Dict[str, Any],
    *,
    store: ProjectWorkspaceStore | None = None,
) -> Dict[str, Any]:
    """Return blockers, in-progress work, upcoming tasks, and derived progress."""
    if not isinstance(payload, Mapping):
        raise TypeError("project_progress_review_payload_must_be_mapping")

    project_id = payload.get("project_id")
    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError("project_progress_review_project_id_required")
    project_id = " ".join(project_id.split())[:160]
    requested_by = payload.get("requested_by") or "local_operator"
    if not isinstance(requested_by, str) or not requested_by.strip():
        raise ValueError("project_progress_review_requested_by_invalid")
    requested_by = " ".join(requested_by.split())[:160]

    result = project_workspace_read_tool({
        "operation": "get",
        "project_id": project_id,
        "requested_by": requested_by,
    }, store=store)
    if result.get("status") != "OK":
        # Preserve owner-hiding semantics from the workspace store.
        return {
            "status": result.get("status", "NOT_FOUND"),
            "reason": result.get("reason", "project_workspace_not_found"),
            "project_id": project_id,
            "workspace_mutated": False,
            "external_actions_executed": False,
        }

    workspace = result.get("workspace")
    if not isinstance(workspace, Mapping):
        raise ValueError("project_progress_review_workspace_invalid")
    raw_tasks = workspace.get("tasks", [])
    tasks = raw_tasks if isinstance(raw_tasks, list) else []

    def task_summary(task: Any) -> dict[str, Any] | None:
        if not isinstance(task, Mapping):
            return None
        item: dict[str, Any] = {
            "task_id": task.get("task_id"),
            "title": task.get("title"),
            "status": task.get("status"),
        }
        for field in ("task_type", "milestone_id", "milestone_name", "priority", "due_in_days", "note"):
            if field in task:
                item[field] = task[field]
        return item

    def select(status: str, *, limit: int = 20) -> list[dict[str, Any]]:
        selected = []
        for task in tasks:
            if not isinstance(task, Mapping) or task.get("status") != status:
                continue
            item = task_summary(task)
            if item is not None:
                selected.append(item)
            if len(selected) >= limit:
                break
        return selected

    blocked_tasks = select("BLOCKED")
    in_progress_tasks = select("IN_PROGRESS")
    todo_tasks = select("TODO", limit=5)
    tracking = workspace.get("task_tracking", {})
    if not isinstance(tracking, Mapping):
        tracking = {}
    milestone_tracking = workspace.get("milestone_tracking", {})
    if not isinstance(milestone_tracking, Mapping):
        milestone_tracking = {}
    project_status = str(workspace.get("status") or "UNKNOWN").upper()

    if project_status == "ARCHIVED":
        suggested_next_step = "The project is archived; review its history rather than changing task state."
    elif project_status == "COMPLETED":
        suggested_next_step = "All project tasks are resolved; review outcomes and archive when appropriate."
    elif project_status == "PAUSED":
        suggested_next_step = "The project is paused; decide whether to resume it before changing task progress."
    elif blocked_tasks:
        suggested_next_step = (
            "Review and resolve the recorded blockers before treating the plan as unblocked."
        )
    elif in_progress_tasks:
        suggested_next_step = (
            "Continue the existing in-progress tasks and record the resulting evidence or blockers."
        )
    elif todo_tasks:
        first = todo_tasks[0]
        suggested_next_step = (
            "Choose whether to start the next listed TODO task: "
            + str(first.get("title") or first.get("task_id") or "unnamed task")
            + "."
        )
    else:
        suggested_next_step = (
            "No TODO, in-progress, or blocked tasks remain in the workspace; verify completion criteria."
        )

    return {
        "status": "OK",
        "review_type": "DETERMINISTIC_READ_ONLY",
        "project_id": project_id,
        "project_title": workspace.get("title", ""),
        "project_status": project_status,
        "workspace_revision": result.get("revision"),
        "goal": workspace.get("goal", ""),
        "task_tracking": dict(tracking),
        "milestone_tracking": dict(milestone_tracking),
        "blocked_tasks": blocked_tasks,
        "in_progress_tasks": in_progress_tasks,
        "next_todo_tasks": todo_tasks,
        "suggested_next_step": suggested_next_step,
        "workspace_mutated": False,
        "external_actions_executed": False,
        "decision_grade_evidence": False,
    }
