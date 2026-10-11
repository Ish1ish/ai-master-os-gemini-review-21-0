"""Canonical S21 HTTP route adapter over the existing unified runtime/O45 bundle.

This module owns transport routing only. It does not create persistence,
governance, identity, or execution authorities; all stateful operations are
delegated to the already-owned runtime instance.
"""
from __future__ import annotations

from typing import Any, Mapping
import uuid
from urllib.parse import parse_qs, urlsplit

from core.src.project_progress_review import project_progress_review_tool
from core.src.project_workspace_store import project_workspace_read_tool


class CanonicalHTTPAPI:
    """Small route adapter for the canonical Python/O45 surface."""

    def __init__(
        self,
        entrypoint,
        *,
        execution_principal: Mapping[str, Any] | None = None,
    ) -> None:
        if entrypoint is None:
            raise ValueError("entrypoint_required")
        self.entrypoint = entrypoint
        self.runtime = entrypoint.runtime
        self.execution_principal = self._principal(
            execution_principal
            or getattr(entrypoint, "execution_principal", None)
        ) or None

    @staticmethod
    def _principal(value: Mapping[str, Any] | None) -> dict[str, Any]:
        value = dict(value or {})
        nested = value.get("principal")
        if isinstance(nested, Mapping):
            value = {
                **dict(nested),
                **{k: v for k, v in value.items() if k != "principal"},
            }
        elif nested and not value.get("principal_id"):
            value["principal_id"] = str(nested)
        if value.get("principal_id") and not value.get("principal"):
            value["principal"] = value["principal_id"]
        return value

    def _authorize(
        self,
        principal: Mapping[str, Any] | None,
        scope: str,
    ) -> dict[str, Any] | None:
        principal = self._principal(principal)
        if principal.get("authenticated") is not True:
            return {
                "status": "UNAUTHORIZED",
                "reason": "principal_not_authenticated",
                "required_scope": scope,
            }
        principal_id = str(
            principal.get("principal_id")
            or principal.get("principal")
            or ""
        ).strip()
        if not principal_id:
            return {
                "status": "UNAUTHORIZED",
                "reason": "principal_required",
                "required_scope": scope,
            }
        scopes = {str(item) for item in (principal.get("scopes") or [])}
        if scope not in scopes:
            return {
                "status": "FORBIDDEN",
                "reason": "scope_not_granted",
                "required_scope": scope,
            }
        return None

    @staticmethod
    def _http_status(result: Mapping[str, Any]) -> int:
        status = str(result.get("status", ""))
        if status == "NOT_FOUND":
            return 404
        if status == "UNAUTHORIZED":
            return 401
        if status in {"FORBIDDEN", "DENY"}:
            return 403
        if status == "BAD_REQUEST":
            return 400
        if status == "CONFLICT":
            return 409
        if status == "UNAVAILABLE":
            return 503
        return 200

    def _submit_workspace_mutation(
        self,
        *,
        project_id: str,
        operation: str,
        body: Mapping[str, Any],
        principal: Mapping[str, Any],
        task_id: str | None = None,
    ) -> tuple[int, dict[str, Any]]:
        """Submit an owner-scoped workspace mutation as an O45-governed intent.

        This method deliberately does not execute the mutation. The caller must
        use the existing explicit /api/intents/{intent_id}/execute route.
        """
        denied = self._authorize(principal, "run:submit")
        if denied:
            return self._http_status(denied), denied

        principal_id = str(
            principal.get("principal_id") or principal.get("principal") or ""
        ).strip()
        if not principal_id:
            result = {"status": "UNAUTHORIZED", "reason": "principal_required"}
            return self._http_status(result), result

        if operation not in {"update_task", "append_note", "record_decision", "update_status"}:
            result = {"status": "BAD_REQUEST", "reason": "project_workspace_operation_invalid"}
            return self._http_status(result), result

        if not project_id.strip() or "/" in project_id or project_id in {".", ".."}:
            result = {"status": "NOT_FOUND", "reason": "canonical_route_not_found"}
            return self._http_status(result), result

        store = getattr(self.entrypoint, "project_workspace_store", None)
        if store is None:
            result = {"status": "UNAVAILABLE", "reason": "project_workspace_store_unavailable"}
            return self._http_status(result), result

        current = project_workspace_read_tool(
            {
                "operation": "get",
                "project_id": project_id,
                "requested_by": principal_id,
            },
            store=store,
        )
        if current.get("status") != "OK":
            result = {
                "status": "NOT_FOUND",
                "reason": "project_workspace_not_found",
                "project_id": project_id,
            }
            return self._http_status(result), result

        workspace = current.get("workspace") or {}
        expected_revision = body.get("expected_revision")
        if (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 1
            or expected_revision > 2**31 - 1
        ):
            result = {"status": "BAD_REQUEST", "reason": "expected_revision_invalid"}
            return self._http_status(result), result

        current_revision = current.get("revision")
        if current_revision != expected_revision:
            result = {
                "status": "CONFLICT",
                "reason": "project_workspace_revision_mismatch",
                "project_id": project_id,
                "expected_revision": expected_revision,
                "current_revision": current_revision,
            }
            return self._http_status(result), result

        project_status = str(workspace.get("status") or "").upper()
        requested_status = None
        if operation == "update_status":
            raw_status = body.get("project_status")
            allowed_project_statuses = {"ACTIVE", "PAUSED", "COMPLETED", "ARCHIVED"}
            if not isinstance(raw_status, str) or raw_status.strip().upper() not in allowed_project_statuses:
                result = {
                    "status": "BAD_REQUEST",
                    "reason": "project_workspace_status_invalid",
                }
                return self._http_status(result), result
            requested_status = raw_status.strip().upper()
            if requested_status == project_status:
                result = {
                    "status": "BAD_REQUEST",
                    "reason": "project_workspace_status_unchanged",
                }
                return self._http_status(result), result

        if project_status == "ARCHIVED":
            result = {
                "status": "CONFLICT",
                "reason": "project_workspace_archived",
                "project_id": project_id,
            }
            return self._http_status(result), result
        if project_status == "COMPLETED" and not (
            operation == "update_status" and requested_status == "ARCHIVED"
        ):
            result = {
                "status": "CONFLICT",
                "reason": "project_workspace_completed",
                "project_id": project_id,
            }
            return self._http_status(result), result
        if project_status == "PAUSED" and operation == "update_task":
            result = {
                "status": "CONFLICT",
                "reason": "project_workspace_paused",
                "project_id": project_id,
            }
            return self._http_status(result), result

        tasks = workspace.get("tasks") if isinstance(workspace.get("tasks"), list) else []
        if operation == "update_task":
            if not isinstance(task_id, str) or not task_id.strip() or "/" in task_id:
                result = {"status": "BAD_REQUEST", "reason": "task_id_invalid"}
                return self._http_status(result), result
            task_id = task_id.strip()
            if not any(isinstance(task, Mapping) and task.get("task_id") == task_id for task in tasks):
                result = {"status": "NOT_FOUND", "reason": "project_workspace_task_not_found", "task_id": task_id}
                return self._http_status(result), result
            task_status = body.get("task_status")
            allowed_statuses = {"TODO", "IN_PROGRESS", "BLOCKED", "DONE", "SKIPPED"}
            if not isinstance(task_status, str) or task_status.strip().upper() not in allowed_statuses:
                result = {"status": "BAD_REQUEST", "reason": "project_workspace_task_status_invalid"}
                return self._http_status(result), result
            note = body.get("note", "")
            if not isinstance(note, str) or len(note) > 1000:
                result = {"status": "BAD_REQUEST", "reason": "project_workspace_task_note_invalid"}
                return self._http_status(result), result
            mutation = {
                "operation": operation,
                "project_id": project_id,
                "expected_revision": expected_revision,
                "task_id": task_id,
                "task_status": task_status.strip().upper(),
                "note": note,
            }

        elif operation == "append_note":
            note = body.get("note")
            if not isinstance(note, str) or not note.strip() or len(note) > 1800:
                result = {"status": "BAD_REQUEST", "reason": "project_workspace_note_invalid"}
                return self._http_status(result), result
            note_type = body.get("note_type", "progress")
            if not isinstance(note_type, str) or note_type.strip().lower() not in {
                "progress", "blocker", "observation", "follow_up"
            }:
                result = {"status": "BAD_REQUEST", "reason": "project_workspace_note_type_invalid"}
                return self._http_status(result), result
            note_task_id = body.get("task_id", "")
            if not isinstance(note_task_id, str):
                result = {"status": "BAD_REQUEST", "reason": "project_workspace_task_id_invalid"}
                return self._http_status(result), result
            note_task_id = note_task_id.strip()
            if note_task_id and not any(
                isinstance(task, Mapping) and task.get("task_id") == note_task_id
                for task in tasks
            ):
                result = {"status": "NOT_FOUND", "reason": "project_workspace_task_not_found", "task_id": note_task_id}
                return self._http_status(result), result
            mutation = {
                "operation": operation,
                "project_id": project_id,
                "expected_revision": expected_revision,
                "note": note,
                "note_type": note_type.strip().lower(),
                "author": principal_id,
                "task_id": note_task_id,
            }

        elif operation == "update_status":
            if requested_status == "COMPLETED":
                unfinished = [
                    str(task.get("task_id") or "")
                    for task in tasks
                    if isinstance(task, Mapping)
                    and str(task.get("status") or "").upper() not in {"DONE", "SKIPPED"}
                ]
                if unfinished:
                    result = {
                        "status": "CONFLICT",
                        "reason": "project_completion_requires_all_tasks_resolved",
                        "project_id": project_id,
                        "unfinished_task_count": len(unfinished),
                        "unfinished_task_ids": unfinished[:20],
                    }
                    return self._http_status(result), result
            mutation = {
                "operation": "update_status",
                "project_id": project_id,
                "expected_revision": expected_revision,
                "project_status": requested_status,
            }

        else:  # record_decision
            title = body.get("title")
            rationale = body.get("rationale")
            if not isinstance(title, str) or not title.strip() or len(title) > 240:
                result = {"status": "BAD_REQUEST", "reason": "project_workspace_decision_title_invalid"}
                return self._http_status(result), result
            if not isinstance(rationale, str) or not rationale.strip() or len(rationale) > 1800:
                result = {"status": "BAD_REQUEST", "reason": "project_workspace_decision_rationale_invalid"}
                return self._http_status(result), result
            source_ids = body.get("source_ids", [])
            if not isinstance(source_ids, list) or any(not isinstance(item, str) for item in source_ids):
                result = {"status": "BAD_REQUEST", "reason": "project_workspace_decision_source_ids_invalid"}
                return self._http_status(result), result
            allowed_source_ids = {
                item.get("source_id")
                for item in (workspace.get("sources") or [])
                if isinstance(item, Mapping)
            }
            if any(item not in allowed_source_ids for item in source_ids):
                result = {"status": "BAD_REQUEST", "reason": "project_workspace_unknown_source_id"}
                return self._http_status(result), result
            mutation = {
                "operation": operation,
                "project_id": project_id,
                "expected_revision": expected_revision,
                "title": title,
                "rationale": rationale,
                "source_ids": list(dict.fromkeys(source_ids)),
                "author": principal_id,
            }

        # The authenticated project owner and route project ID are the only
        # identity/scope values copied into the governed operation.
        run_id = "S21-HTTP-WS-" + uuid.uuid4().hex
        submission_payload = {
            "run_id": run_id,
            "project_id": project_id,
            "strategy_id": "S21-HTTP-WS-STRATEGY-" + uuid.uuid4().hex[:16],
            "intent": "Update project workspace using " + operation,
            "goal": str(workspace.get("goal") or ""),
            "audience": str(workspace.get("audience") or ""),
            "requested_language": "en",
            "execution_contract": {
                "action": "update_project_workspace",
                "tool_name": "provider.project.workspace.write",
                "payload": mutation,
            },
        }
        result = self.entrypoint.run(submission_payload, principal=principal)
        return self._http_status(result), result

    def handle(
        self,
        *,
        method: str,
        path: str,
        body: Mapping[str, Any] | None,
        principal: Mapping[str, Any] | None,
    ) -> tuple[int, dict[str, Any]]:
        route = urlsplit(path).path.rstrip("/") or "/"
        body = dict(body or {})
        principal = self._principal(principal)

        if method == "POST" and route == "/api/runs":
            denied = self._authorize(principal, "run:submit")
            if denied:
                return self._http_status(denied), denied
            result = self.entrypoint.run(body, principal=principal)
            return self._http_status(result), result

        if (
            method == "POST"
            and route.startswith("/api/intents/")
            and route.endswith("/execute")
        ):
            intent_id = route[len("/api/intents/") : -len("/execute")].strip("/")
            if not intent_id:
                result = {"status": "BAD_REQUEST", "reason": "intent_id_required"}
                return self._http_status(result), result
            denied = self._authorize(principal, "run:execute")
            if denied:
                return self._http_status(denied), denied
            result = self.runtime.execute_governed_intent(
                intent_id,
                principal=self.execution_principal or principal,
            )
            return self._http_status(result), result

        if method == "POST" and route.startswith("/api/projects/"):
            project_path = route[len("/api/projects/"):]
            segments = project_path.split("/")
            if len(segments) == 3 and segments[1] == "tasks":
                project_id, _tasks, task_id = segments
                return self._submit_workspace_mutation(
                    project_id=project_id,
                    operation="update_task",
                    body=body,
                    principal=principal,
                    task_id=task_id,
                )
            if len(segments) == 2 and segments[1] in {"notes", "decisions", "status"}:
                project_id, suffix = segments
                operation = {
                    "notes": "append_note",
                    "decisions": "record_decision",
                    "status": "update_status",
                }[suffix]
                return self._submit_workspace_mutation(
                    project_id=project_id,
                    operation=operation,
                    body=body,
                    principal=principal,
                )
            result = {"status": "NOT_FOUND", "reason": "canonical_route_not_found"}
            return self._http_status(result), result

        if method == "GET" and route == "/api/projects":
            denied = self._authorize(principal, "run:read")
            if denied:
                return self._http_status(denied), denied
            query = parse_qs(urlsplit(path).query)
            raw_limit = (query.get("limit") or ["20"])[0]
            try:
                limit = int(raw_limit)
            except (TypeError, ValueError):
                result = {"status": "BAD_REQUEST", "reason": "project_limit_invalid"}
                return self._http_status(result), result
            if limit < 1 or limit > 100:
                result = {"status": "BAD_REQUEST", "reason": "project_limit_out_of_range"}
                return self._http_status(result), result
            store = getattr(self.entrypoint, "project_workspace_store", None)
            if store is None:
                result = {"status": "UNAVAILABLE", "reason": "project_workspace_store_unavailable"}
                return self._http_status(result), result
            principal_id = str(principal.get("principal_id") or principal.get("principal") or "").strip()
            result = project_workspace_read_tool(
                {"operation": "list", "limit": limit, "requested_by": principal_id},
                store=store,
            )
            return self._http_status(result), result

        if method == "GET" and route.startswith("/api/projects/"):
            project_path = route[len("/api/projects/"):]
            is_review = project_path.endswith("/review")
            project_id = (
                project_path[:-len("/review")].strip("/")
                if is_review else project_path.strip("/")
            )
            if not project_id or "/" in project_id:
                result = {"status": "NOT_FOUND", "reason": "canonical_route_not_found"}
                return self._http_status(result), result
            denied = self._authorize(principal, "run:read")
            if denied:
                return self._http_status(denied), denied
            store = getattr(self.entrypoint, "project_workspace_store", None)
            if store is None:
                result = {"status": "UNAVAILABLE", "reason": "project_workspace_store_unavailable"}
                return self._http_status(result), result
            principal_id = str(principal.get("principal_id") or principal.get("principal") or "").strip()
            if is_review:
                result = project_progress_review_tool(
                    {"project_id": project_id, "requested_by": principal_id},
                    store=store,
                )
            else:
                result = project_workspace_read_tool(
                    {
                        "operation": "get",
                        "project_id": project_id,
                        "requested_by": principal_id,
                    },
                    store=store,
                )
            return self._http_status(result), result

        if method == "GET" and route == "/api/approvals":
            denied = self._authorize(principal, "approval:read")
            if denied:
                return self._http_status(denied), denied
            return 200, {
                "status": "OK",
                "approvals": self.runtime.list_approvals(),
            }

        if method == "GET" and route.startswith("/api/approvals/"):
            approval_id = route[len("/api/approvals/") :].strip("/")
            if not approval_id:
                result = {"status": "BAD_REQUEST", "reason": "approval_id_required"}
                return self._http_status(result), result
            denied = self._authorize(principal, "approval:read")
            if denied:
                return self._http_status(denied), denied
            result = self.runtime.get_approval(approval_id)
            return self._http_status(result), result

        if (
            method == "POST"
            and route.startswith("/api/approvals/")
            and route.endswith("/decision")
        ):
            approval_id = route[len("/api/approvals/") : -len("/decision")].strip("/")
            if not approval_id or "/" in approval_id:
                result = {
                    "status": "NOT_FOUND",
                    "reason": "canonical_route_not_found",
                }
                return self._http_status(result), result
            denied = self._authorize(principal, "approval:decide")
            if denied:
                return self._http_status(denied), denied
            result = self.runtime.decide_approval(
                approval_id,
                principal=principal,
                decision=str(body.get("decision") or ""),
                reason=str(body.get("reason") or ""),
            )
            return self._http_status(result), result

        if method == "GET" and route.startswith("/api/executions/"):
            execution_id = route[len("/api/executions/") :].strip("/")
            if not execution_id:
                result = {"status": "BAD_REQUEST", "reason": "execution_id_required"}
                return self._http_status(result), result
            denied = self._authorize(principal, "run:read")
            if denied:
                return self._http_status(denied), denied
            result = self.runtime.get_execution(execution_id)
            return self._http_status(result), result

        if method == "GET" and route == "/api/experiments":
            denied = self._authorize(principal, "experiment:read")
            if denied:
                return self._http_status(denied), denied
            query = parse_qs(urlsplit(path).query)
            project_id = (query.get("project_id") or [None])[0]
            limit = (query.get("limit") or ["50"])[0]
            try:
                parsed_limit = int(limit)
            except (TypeError, ValueError):
                result = {"status": "BAD_REQUEST", "reason": "limit_invalid"}
                return self._http_status(result), result
            result = {
                "status": "OK",
                "experiments": self.runtime.list_experiments(project_id=project_id, limit=parsed_limit),
            }
            return self._http_status(result), result

        if method == "GET" and route.startswith("/api/experiments/"):
            experiment_id = route[len("/api/experiments/") :].strip("/")
            if not experiment_id or "/" in experiment_id:
                result = {"status": "NOT_FOUND", "reason": "canonical_route_not_found"}
                return self._http_status(result), result
            denied = self._authorize(principal, "experiment:read")
            if denied:
                return self._http_status(denied), denied
            result = self.runtime.get_experiment(experiment_id)
            return self._http_status(result), result

        if (
            method == "POST"
            and route.startswith("/api/experiments/")
            and route.endswith("/evidence")
        ):
            experiment_id = route[len("/api/experiments/") : -len("/evidence")].strip("/")
            if not experiment_id or "/" in experiment_id:
                result = {"status": "NOT_FOUND", "reason": "canonical_route_not_found"}
                return self._http_status(result), result
            denied = self._authorize(principal, "experiment:write")
            if denied:
                return self._http_status(denied), denied
            result = self.runtime.record_experiment_evidence(experiment_id, body)
            return self._http_status(result), result

        if (
            method == "POST"
            and route.startswith("/api/experiments/")
            and route.endswith("/evaluate")
        ):
            experiment_id = route[len("/api/experiments/") : -len("/evaluate")].strip("/")
            if not experiment_id or "/" in experiment_id:
                result = {"status": "NOT_FOUND", "reason": "canonical_route_not_found"}
                return self._http_status(result), result
            denied = self._authorize(principal, "experiment:evaluate")
            if denied:
                return self._http_status(denied), denied
            result = self.runtime.evaluate_experiment(experiment_id)
            return self._http_status(result), result

        if method == "GET" and route == "/api/learning/context":
            denied = self._authorize(principal, "learning:read")
            if denied:
                return self._http_status(denied), denied
            query = parse_qs(urlsplit(path).query)
            project_id = (query.get("project_id") or [""])[0].strip()
            if not project_id:
                result = {"status": "BAD_REQUEST", "reason": "project_id_required"}
                return self._http_status(result), result
            experiment_id = (query.get("experiment_id") or [None])[0]
            result = self.runtime.get_learning_context(
                project_id,
                current_experiment_id=experiment_id,
            )
            return self._http_status(result), result

        return 404, {
            "status": "NOT_FOUND",
            "reason": "canonical_route_not_found",
        }
