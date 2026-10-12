"""SQLite-backed project workspace with revisioned snapshots and event history.

The workspace persists project plans, task state, progress notes, and decisions
between runs. Mutations are explicit, version-checked, and auditable; this
module never executes tasks, publishes content, or spends funds.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping
from urllib.parse import urlsplit, urlunsplit


MAX_WORKSPACE_TASKS = 160
MAX_WORKSPACE_NOTES = 500
MAX_WORKSPACE_DECISIONS = 200
MAX_WORKSPACE_EVENTS = 100


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _text(value: Any, field: str, *, required: bool = True, limit: int = 1800) -> str:
    if not isinstance(value, str):
        if value is None and not required:
            return ""
        raise ValueError("project_workspace_invalid:" + field)
    rendered = " ".join(value.split())[:limit]
    if required and not rendered:
        raise ValueError("project_workspace_invalid:" + field)
    return rendered


def _bounded_int(value: Any, field: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < low or value > high:
        raise ValueError("project_workspace_invalid:" + field)
    return value


def _sha256(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _source_map(value: Any) -> tuple[list[dict[str, Any]], set[str]]:
    if not isinstance(value, list) or not value or len(value) > 20:
        raise ValueError("project_workspace_sources_required")
    sources = []
    ids: set[str] = set()
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError("project_workspace_source_invalid")
        source_id = _text(item.get("source_id"), "source_id", limit=20)
        url = _text(item.get("url"), "source_url", limit=1800)
        if source_id in ids or not re.fullmatch(r"S[0-9]{3,6}", source_id):
            raise ValueError("project_workspace_source_id_invalid")
        try:
            parsed = urlsplit(url)
        except ValueError as exc:
            raise ValueError("project_workspace_source_url_invalid") from exc
        if (
            parsed.scheme.lower() not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise ValueError("project_workspace_source_url_invalid")
        normalized_url = urlunsplit((
            parsed.scheme.lower(),
            parsed.netloc,
            parsed.path,
            parsed.query,
            "",
        ))
        if any(existing["url"].casefold() == normalized_url.casefold() for existing in sources):
            raise ValueError("project_workspace_source_url_duplicate")
        ids.add(source_id)
        hostname = (parsed.hostname or "").lower()
        if hostname.startswith("www."):
            hostname = hostname[4:]
        source = {
            "source_id": source_id,
            "url": normalized_url,
            "title": _text(item.get("title") or hostname or source_id, "source_title", limit=240),
            "domain": hostname,
        }
        for key in ("published_at", "accessed_at"):
            val = item.get(key)
            if val:
                source[key] = _text(val, key, limit=100)
        matches = item.get("matched_queries")
        if isinstance(matches, list):
            source["matched_queries"] = [
                _text(match, "matched_query", limit=700)
                for match in matches[:6]
                if isinstance(match, str) and match.strip()
            ]
        sources.append(source)
    return sources, ids


def _build_tasks(plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    milestones = plan.get("milestones")
    if not isinstance(milestones, list):
        raise ValueError("project_workspace_milestones_required")
    for milestone_index, milestone in enumerate(milestones, start=1):
        if not isinstance(milestone, Mapping):
            raise ValueError("project_workspace_milestone_invalid")
        milestone_id = f"M{milestone_index:02d}"
        milestone_name = _text(milestone.get("name"), "milestone_name", limit=180)
        raw_tasks = milestone.get("tasks")
        if not isinstance(raw_tasks, list):
            raise ValueError("project_workspace_milestone_tasks_invalid")
        for task_index, raw_task in enumerate(raw_tasks, start=1):
            title = _text(raw_task, "task_title", limit=500)
            tasks.append({
                "task_id": f"{milestone_id}-T{task_index:02d}",
                "task_type": "milestone",
                "milestone_id": milestone_id,
                "milestone_name": milestone_name,
                "title": title,
                "status": "TODO",
                "note": "",
                "created_at": _now(),
                "updated_at": _now(),
            })
    next_actions = plan.get("next_actions", [])
    if next_actions:
        if not isinstance(next_actions, list):
            raise ValueError("project_workspace_next_actions_invalid")
        for index, action in enumerate(next_actions, start=1):
            if not isinstance(action, Mapping):
                raise ValueError("project_workspace_next_action_invalid")
            task = {
                "task_id": f"A{index:02d}",
                "task_type": "next_action",
                "title": _text(action.get("action"), "next_action_title", limit=500),
                "status": "TODO",
                "note": "",
                "created_at": _now(),
                "updated_at": _now(),
            }
            for key in ("priority", "due_in_days", "success_criteria"):
                if key in action:
                    task[key] = action[key]
            tasks.append(task)
    if not tasks or len(tasks) > MAX_WORKSPACE_TASKS:
        raise ValueError("project_workspace_task_count_invalid")
    task_ids = [task["task_id"] for task in tasks]
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("project_workspace_task_id_duplicate")
    return tasks


def _progress(tasks: list[dict[str, Any]]) -> dict[str, int]:
    total = len(tasks)
    completed = sum(1 for task in tasks if task.get("status") in {"DONE", "SKIPPED"})
    done = sum(1 for task in tasks if task.get("status") == "DONE")
    blocked = sum(1 for task in tasks if task.get("status") == "BLOCKED")
    in_progress = sum(1 for task in tasks if task.get("status") == "IN_PROGRESS")
    return {
        "task_count": total,
        "completed_task_count": completed,
        "done_task_count": done,
        "in_progress_task_count": in_progress,
        "blocked_task_count": blocked,
        "progress_percent": int(round((completed / total) * 100)) if total else 0,
    }


def _milestone_progress(plan: Any, tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive milestone-level progress from task state without storing duplicates."""
    raw_milestones = plan.get("milestones", []) if isinstance(plan, Mapping) else []
    if not isinstance(raw_milestones, list):
        raw_milestones = []

    milestones: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_milestones, start=1):
        if not isinstance(raw, Mapping):
            continue
        milestone_id = f"M{index:02d}"
        related = [task for task in tasks if task.get("milestone_id") == milestone_id]
        counts = _progress(related)
        if counts["task_count"] and counts["completed_task_count"] == counts["task_count"]:
            status = "DONE"
        elif counts["blocked_task_count"]:
            status = "BLOCKED"
        elif counts["in_progress_task_count"] or counts["completed_task_count"]:
            status = "IN_PROGRESS"
        else:
            status = "TODO"
        entry: dict[str, Any] = {
            "milestone_id": milestone_id,
            "name": raw.get("name", milestone_id),
            "status": status,
            "task_tracking": counts,
        }
        for field in ("duration_days", "objective", "completion_criteria"):
            if field in raw:
                entry[field] = raw[field]
        milestones.append(entry)

    count = len(milestones)
    return {
        "milestone_count": count,
        "completed_milestone_count": sum(1 for item in milestones if item["status"] == "DONE"),
        "in_progress_milestone_count": sum(1 for item in milestones if item["status"] == "IN_PROGRESS"),
        "blocked_milestone_count": sum(1 for item in milestones if item["status"] == "BLOCKED"),
        # Weight overall milestone progress by tasks so empty milestones don't
        # inflate or suppress the project's aggregate completion percentage.
        "progress_percent": _progress(tasks)["progress_percent"],
        "milestones": milestones,
    }


class ProjectWorkspaceStore:
    """Persistent project snapshot store with optimistic revision checks."""

    TASK_STATUSES = {"TODO", "IN_PROGRESS", "BLOCKED", "DONE", "SKIPPED"}
    PROJECT_STATUSES = {"ACTIVE", "PAUSED", "COMPLETED", "ARCHIVED"}

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS project_workspaces (
                    project_id TEXT PRIMARY KEY,
                    revision INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    plan_fingerprint TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS project_workspace_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES project_workspaces(project_id)
                );
                CREATE INDEX IF NOT EXISTS idx_workspace_events_project_revision
                  ON project_workspace_events(project_id, revision DESC);
                """
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    @staticmethod
    def _decode_snapshot(row: sqlite3.Row) -> dict[str, Any]:
        snapshot = json.loads(row["snapshot_json"])
        if not isinstance(snapshot, dict):
            raise RuntimeError("project_workspace_snapshot_corrupt")
        return snapshot

    def _events(self, conn: sqlite3.Connection, project_id: str, limit: int = 25) -> list[dict[str, Any]]:
        rows = conn.execute(
            "SELECT event_id, revision, event_type, payload_json, created_at "
            "FROM project_workspace_events WHERE project_id=? ORDER BY event_id DESC LIMIT ?",
            (project_id, limit),
        ).fetchall()
        return [
            {
                "event_id": row["event_id"],
                "revision": row["revision"],
                "event_type": row["event_type"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in reversed(rows)
        ]

    def _result(self, conn: sqlite3.Connection, row: sqlite3.Row, status: str = "OK") -> dict[str, Any]:
        snapshot = self._decode_snapshot(row)
        snapshot["task_tracking"] = _progress(snapshot.get("tasks", []))
        snapshot["milestone_tracking"] = _milestone_progress(
            snapshot.get("plan", {}),
            snapshot.get("tasks", []),
        )
        return {
            "status": status,
            "revision": row["revision"],
            "workspace": snapshot,
            "events": self._events(conn, row["project_id"]),
        }

    def read(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise TypeError("project_workspace_read_payload_must_be_mapping")
        operation = _text(payload.get("operation"), "operation", limit=30).lower()
        with closing(self._connect()) as conn:
            if operation == "get":
                project_id = _text(payload.get("project_id"), "project_id", limit=160)
                row = conn.execute(
                    "SELECT * FROM project_workspaces WHERE project_id=?",
                    (project_id,),
                ).fetchone()
                if row is None:
                    return {"status": "NOT_FOUND", "reason": "project_workspace_not_found", "project_id": project_id}
                requested_by = _text(payload.get("requested_by") or "local_operator", "requested_by", limit=160)
                if self._decode_snapshot(row).get("owner_id", "local_operator") != requested_by:
                    return {"status": "NOT_FOUND", "reason": "project_workspace_not_found", "project_id": project_id}
                return self._result(conn, row)

            if operation == "list":
                limit = _bounded_int(payload.get("limit", 20), "limit", 1, 100)
                requested_by = _text(payload.get("requested_by") or "local_operator", "requested_by", limit=160)
                rows = conn.execute(
                    "SELECT project_id, revision, title, status, created_at, updated_at, snapshot_json "
                    "FROM project_workspaces ORDER BY updated_at DESC",
                ).fetchall()
                projects = []
                for row in rows:
                    snapshot = json.loads(row["snapshot_json"])
                    if snapshot.get("owner_id", "local_operator") != requested_by:
                        continue
                    projects.append({
                        "project_id": row["project_id"],
                        "revision": row["revision"],
                        "title": row["title"],
                        "status": row["status"],
                        "goal": snapshot.get("goal", ""),
                        "updated_at": row["updated_at"],
                        "task_tracking": _progress(snapshot.get("tasks", [])),
                        "milestone_tracking": _milestone_progress(
                            snapshot.get("plan", {}),
                            snapshot.get("tasks", []),
                        ),
                    })
                    if len(projects) >= limit:
                        break
                return {"status": "OK", "count": len(projects), "projects": projects}
            raise ValueError("project_workspace_read_operation_unsupported")

    def write(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise TypeError("project_workspace_write_payload_must_be_mapping")
        operation = _text(payload.get("operation"), "operation", limit=40).lower()
        if operation == "create_from_plan":
            return self._create_from_plan(payload)
        if operation in {"add_task", "update_task", "append_note", "record_decision", "update_status"}:
            return self._mutate(payload, operation)
        raise ValueError("project_workspace_write_operation_unsupported")

    def _create_from_plan(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        project_id = _text(payload.get("project_id"), "project_id", limit=160)
        plan_result = payload.get("plan_result")
        if not isinstance(plan_result, Mapping):
            raise ValueError("project_workspace_plan_result_required")
        if plan_result.get("plan_type") != "INTERNAL_DRAFT" or plan_result.get("decision_grade_evidence") is not False:
            raise ValueError("project_workspace_plan_boundary_invalid")
        result_status = str(plan_result.get("status") or "").upper()
        if result_status not in {"COMPLETE", "PARTIAL"}:
            raise ValueError("project_workspace_plan_result_status_invalid")
        generation_status = str(plan_result.get("generation_status") or ("COMPLETE" if result_status == "COMPLETE" else ""))
        if generation_status != "COMPLETE":
            raise ValueError("project_workspace_plan_not_complete")
        plan = plan_result.get("plan")
        if not isinstance(plan, Mapping):
            raise ValueError("project_workspace_plan_body_required")
        sources, source_ids = _source_map(plan_result.get("sources"))
        for finding_group in ("assumptions", "risks", "budget_items"):
            items = plan.get(finding_group, [])
            if not isinstance(items, list):
                raise ValueError("project_workspace_plan_schema_invalid")
            for item in items:
                if not isinstance(item, Mapping):
                    raise ValueError("project_workspace_plan_schema_invalid")
                refs = item.get("source_ids", [])
                if not isinstance(refs, list) or any(not isinstance(ref, str) or ref not in source_ids for ref in refs):
                    raise ValueError("project_workspace_plan_unknown_source_id")
                if finding_group == "budget_items" and item.get("basis") == "source_supported" and not refs:
                    raise ValueError("project_workspace_plan_citation_required")
        tasks = _build_tasks(plan)
        now = _now()
        goal = _text(plan_result.get("project_goal"), "project_goal", limit=500)
        title = _text(plan.get("project_title"), "project_title", limit=200)
        owner_id = _text(payload.get("requested_by") or "local_operator", "requested_by", limit=160)
        status = "ACTIVE"
        fingerprint_basis = {
            "project_id": project_id,
            "goal": goal,
            "plan": dict(plan),
            "sources": sources,
        }
        fingerprint = _sha256(fingerprint_basis)
        snapshot = {
            "project_id": project_id,
            "owner_id": owner_id,
            "title": title,
            "goal": goal,
            "audience": _text(plan_result.get("audience") or "", "audience", required=False, limit=240),
            "status": status,
            "revision": 1,
            "created_at": now,
            "updated_at": now,
            "plan_type": "INTERNAL_DRAFT",
            "plan": dict(plan),
            "sources": sources,
            "research_status": _text(plan_result.get("research_status") or "UNKNOWN", "research_status", limit=20),
            "evidence_boundary": _text(plan_result.get("evidence_boundary") or "", "evidence_boundary", required=False, limit=180),
            "decision_grade_evidence": False,
            "budget": {
                "user_budget": _text(plan_result.get("user_budget") or "", "user_budget", required=False, limit=140),
                "currency": _text(plan_result.get("budget_currency") or "unspecified", "budget_currency", limit=20),
                "note": _text(plan_result.get("budget_note") or "", "budget_note", required=False, limit=500),
            },
            "tasks": tasks,
            "notes": [],
            "decisions": [],
            "external_actions_executed": False,
            "task_tracking": _progress(tasks),
        }
        with closing(self._connect()) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                existing = conn.execute(
                    "SELECT * FROM project_workspaces WHERE project_id=?", (project_id,)
                ).fetchone()
                if existing is not None:
                    existing_snapshot = self._decode_snapshot(existing)
                    if existing_snapshot.get("owner_id", "local_operator") != owner_id:
                        conn.rollback()
                        return {
                            "status": "CONFLICT",
                            "reason": "project_workspace_already_exists",
                            "project_id": project_id,
                        }
                    if existing["plan_fingerprint"] == fingerprint:
                        conn.rollback()
                        return self._result(conn, existing, "IDEMPOTENT_REPLAY")
                    conn.rollback()
                    return {
                        "status": "CONFLICT",
                        "reason": "project_workspace_already_exists",
                        "project_id": project_id,
                        "current_revision": existing["revision"],
                    }
                conn.execute(
                    "INSERT INTO project_workspaces(project_id, revision, title, status, plan_fingerprint, snapshot_json, created_at, updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?)",
                    (project_id, 1, title, status, fingerprint, _json(snapshot), now, now),
                )
                conn.execute(
                    "INSERT INTO project_workspace_events(project_id, revision, event_type, payload_json, created_at) VALUES(?,?,?,?,?)",
                    (project_id, 1, "CREATED_FROM_PLAN", _json({"title": title, "goal": goal, "source_count": len(sources), "task_count": len(tasks)}), now),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT * FROM project_workspaces WHERE project_id=?", (project_id,)
                ).fetchone()
                return self._result(conn, row, "CREATED")
            except Exception:
                conn.rollback()
                raise

    def _mutate(self, payload: Mapping[str, Any], operation: str) -> Dict[str, Any]:
        project_id = _text(payload.get("project_id"), "project_id", limit=160)
        expected_revision = _bounded_int(payload.get("expected_revision"), "expected_revision", 1, 2**31 - 1)
        now = _now()
        with closing(self._connect()) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    "SELECT * FROM project_workspaces WHERE project_id=?", (project_id,)
                ).fetchone()
                if row is None:
                    conn.rollback()
                    return {"status": "NOT_FOUND", "reason": "project_workspace_not_found", "project_id": project_id}
                snapshot = self._decode_snapshot(row)
                requested_by = _text(payload.get("requested_by") or "local_operator", "requested_by", limit=160)
                # Enforce owner scope before checking revision so another owner
                # cannot use conflicts to infer the current revision.
                if snapshot.get("owner_id", "local_operator") != requested_by:
                    conn.rollback()
                    return {"status": "NOT_FOUND", "reason": "project_workspace_not_found", "project_id": project_id}

                current_revision = int(row["revision"])
                if current_revision != expected_revision:
                    conn.rollback()
                    return {
                        "status": "CONFLICT",
                        "reason": "project_workspace_revision_mismatch",
                        "project_id": project_id,
                        "expected_revision": expected_revision,
                        "current_revision": current_revision,
                    }

                current_status = snapshot.get("status")
                if current_status == "ARCHIVED":
                    conn.rollback()
                    return {"status": "CONFLICT", "reason": "project_workspace_archived", "project_id": project_id}
                if current_status == "PAUSED" and operation in {"update_task", "add_task"}:
                    conn.rollback()
                    return {"status": "CONFLICT", "reason": "project_workspace_paused", "project_id": project_id}
                if current_status == "COMPLETED":
                    requested_status = str(payload.get("project_status") or "").strip().upper()
                    if operation != "update_status" or requested_status != "ARCHIVED":
                        conn.rollback()
                        return {"status": "CONFLICT", "reason": "project_workspace_completed", "project_id": project_id}
                event_payload: dict[str, Any] = {}

                if operation == "update_task":
                    task_id = _text(payload.get("task_id"), "task_id", limit=40)
                    task_status = _text(payload.get("task_status"), "task_status", limit=20).upper()
                    if task_status not in self.TASK_STATUSES:
                        raise ValueError("project_workspace_task_status_invalid")
                    task = next((item for item in snapshot["tasks"] if item["task_id"] == task_id), None)
                    if task is None:
                        conn.rollback()
                        return {"status": "NOT_FOUND", "reason": "project_workspace_task_not_found", "task_id": task_id}
                    note = _text(payload.get("note") or "", "note", required=False, limit=1000)
                    task["status"] = task_status
                    task["note"] = note
                    task["updated_at"] = now
                    event_payload = {"task_id": task_id, "task_status": task_status, "note": note}

                elif operation == "add_task":
                    if len(snapshot.get("tasks", [])) >= MAX_WORKSPACE_TASKS:
                        raise ValueError("project_workspace_task_limit_reached")
                    title = _text(payload.get("title"), "task_title", limit=500)
                    note = _text(payload.get("note") or "", "task_note", required=False, limit=1000)
                    author = _text(payload.get("author") or "operator", "author", limit=100)
                    existing_ids = {str(task.get("task_id") or "") for task in snapshot["tasks"]}
                    sequence = 1
                    while f"X{sequence:03d}" in existing_ids:
                        sequence += 1
                    task = {
                        "task_id": f"X{sequence:03d}",
                        "task_type": "ad_hoc",
                        "title": title,
                        "status": "TODO",
                        "note": note,
                        "created_at": now,
                        "updated_at": now,
                    }

                    raw_plan = snapshot.get("plan", {})
                    raw_milestones = raw_plan.get("milestones", []) if isinstance(raw_plan, Mapping) else []
                    milestone_id = _text(
                        payload.get("milestone_id") or "",
                        "milestone_id",
                        required=False,
                        limit=20,
                    )
                    if milestone_id:
                        milestone = next(
                            (
                                item for index, item in enumerate(raw_milestones, start=1)
                                if isinstance(item, Mapping) and f"M{index:02d}" == milestone_id
                            ),
                            None,
                        )
                        if milestone is None:
                            raise ValueError("project_workspace_milestone_not_found")
                        task["milestone_id"] = milestone_id
                        task["milestone_name"] = _text(
                            milestone.get("name") or milestone_id,
                            "milestone_name",
                            limit=180,
                        )

                    priority = _text(
                        payload.get("priority") or "",
                        "task_priority",
                        required=False,
                        limit=20,
                    ).lower()
                    if priority:
                        if priority not in {"low", "medium", "high", "urgent"}:
                            raise ValueError("project_workspace_task_priority_invalid")
                        task["priority"] = priority

                    if "due_in_days" in payload and payload.get("due_in_days") is not None:
                        task["due_in_days"] = _bounded_int(
                            payload.get("due_in_days"),
                            "due_in_days",
                            0,
                            3650,
                        )

                    success_criteria = _text(
                        payload.get("success_criteria") or "",
                        "success_criteria",
                        required=False,
                        limit=700,
                    )
                    if success_criteria:
                        task["success_criteria"] = success_criteria

                    snapshot["tasks"].append(task)
                    event_payload = dict(task)
                    event_payload["author"] = author

                elif operation == "append_note":
                    if len(snapshot["notes"]) >= MAX_WORKSPACE_NOTES:
                        raise ValueError("project_workspace_note_limit_reached")
                    note_text = _text(payload.get("note"), "note", limit=1800)
                    note_type = _text(payload.get("note_type") or "progress", "note_type", limit=30).lower()
                    if note_type not in {"progress", "blocker", "observation", "follow_up"}:
                        raise ValueError("project_workspace_note_type_invalid")
                    author = _text(payload.get("author") or "operator", "author", limit=100)
                    task_id = _text(payload.get("task_id") or "", "task_id", required=False, limit=40)
                    if task_id and not any(item["task_id"] == task_id for item in snapshot["tasks"]):
                        raise ValueError("project_workspace_task_not_found")
                    item = {"note_id": f"N{len(snapshot['notes']) + 1:04d}", "text": note_text, "note_type": note_type, "author": author, "task_id": task_id, "created_at": now}
                    snapshot["notes"].append(item)
                    event_payload = dict(item)

                elif operation == "record_decision":
                    if len(snapshot["decisions"]) >= MAX_WORKSPACE_DECISIONS:
                        raise ValueError("project_workspace_decision_limit_reached")
                    decision_title = _text(payload.get("title"), "decision_title", limit=240)
                    rationale = _text(payload.get("rationale"), "decision_rationale", limit=1800)
                    allowed_ids = {item["source_id"] for item in snapshot["sources"]}
                    source_ids = payload.get("source_ids", [])
                    if not isinstance(source_ids, list) or any(not isinstance(ref, str) or ref not in allowed_ids for ref in source_ids):
                        raise ValueError("project_workspace_unknown_source_id")
                    source_ids = list(dict.fromkeys(source_ids))
                    author = _text(payload.get("author") or "operator", "author", limit=100)
                    item = {"decision_id": f"D{len(snapshot['decisions']) + 1:04d}", "title": decision_title, "rationale": rationale, "source_ids": source_ids, "author": author, "created_at": now}
                    snapshot["decisions"].append(item)
                    event_payload = dict(item)

                elif operation == "update_status":
                    new_status = _text(payload.get("project_status"), "project_status", limit=20).upper()
                    if new_status not in self.PROJECT_STATUSES:
                        raise ValueError("project_workspace_status_invalid")
                    if new_status == "COMPLETED":
                        unfinished = [task["task_id"] for task in snapshot["tasks"] if task["status"] not in {"DONE", "SKIPPED"}]
                        if unfinished:
                            raise ValueError("project_completion_requires_all_tasks_resolved")
                    old_status = snapshot["status"]
                    snapshot["status"] = new_status
                    event_payload = {"old_status": old_status, "new_status": new_status}
                else:
                    raise ValueError("project_workspace_write_operation_unsupported")

                revision = current_revision + 1
                snapshot["revision"] = revision
                snapshot["updated_at"] = now
                snapshot["task_tracking"] = _progress(snapshot.get("tasks", []))
                conn.execute(
                    "UPDATE project_workspaces SET revision=?, title=?, status=?, snapshot_json=?, updated_at=? WHERE project_id=?",
                    (revision, snapshot["title"], snapshot["status"], _json(snapshot), now, project_id),
                )
                conn.execute(
                    "INSERT INTO project_workspace_events(project_id, revision, event_type, payload_json, created_at) VALUES(?,?,?,?,?)",
                    (project_id, revision, operation.upper(), _json(event_payload), now),
                )
                conn.commit()
                updated = conn.execute(
                    "SELECT * FROM project_workspaces WHERE project_id=?", (project_id,)
                ).fetchone()
                return self._result(conn, updated, "UPDATED")
            except Exception:
                conn.rollback()
                raise


def _default_store() -> ProjectWorkspaceStore:
    path = os.getenv("AI_OS_PROJECT_WORKSPACE_DB_PATH", "./data/project_workspace.sqlite3")
    return ProjectWorkspaceStore(path)


def project_workspace_read_tool(payload: Dict[str, Any], *, store: ProjectWorkspaceStore | None = None) -> Dict[str, Any]:
    """O45 read handler: supports get/list only."""
    if not isinstance(payload, Mapping):
        raise TypeError("project_workspace_read_payload_must_be_mapping")
    operation = str(payload.get("operation") or "").strip().lower()
    if operation not in {"get", "list"}:
        raise ValueError("project_workspace_read_operation_unsupported")
    return (store or _default_store()).read(dict(payload))


def project_workspace_write_tool(payload: Dict[str, Any], *, store: ProjectWorkspaceStore | None = None) -> Dict[str, Any]:
    """O45 write handler: supports create/update mutations only."""
    if not isinstance(payload, Mapping):
        raise TypeError("project_workspace_write_payload_must_be_mapping")
    operation = str(payload.get("operation") or "").strip().lower()
    if operation not in {"create_from_plan", "add_task", "update_task", "append_note", "record_decision", "update_status"}:
        raise ValueError("project_workspace_write_operation_unsupported")
    return (store or _default_store()).write(dict(payload))
