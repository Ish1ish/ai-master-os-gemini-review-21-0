from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class OptimizationStore:
    """Durable, auditable state for bounded self-optimization proposals.

    The store records planning/evaluation/approval/application/rollback evidence.
    It never executes an external action itself.
    """

    def __init__(self, path: str = "./data/optimization.sqlite3"):
        self.path = str(path)
        if self.path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS optimization_changes(
                change_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                evaluation_json TEXT,
                governance_json TEXT,
                outcome_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.conn.commit()
        self._closed = False

    def _assert_open(self) -> None:
        if self._closed or self.conn is None:
            raise RuntimeError("optimization_store_closed")

    def create(self, change_id: str, project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._assert_open()
        now = _utc_now()
        record = {
            "change_id": str(change_id),
            "project_id": str(project_id),
            "status": "PROPOSED",
            "payload": _json_safe(payload),
            "evaluation": None,
            "governance": None,
            "outcome": None,
            "created_at": now,
            "updated_at": now,
        }
        with self._lock:
            existing = self.conn.execute(
                "SELECT * FROM optimization_changes WHERE change_id=?", (record["change_id"],)
            ).fetchone()
            if existing:
                return self._row(existing)
            self.conn.execute(
                "INSERT INTO optimization_changes(change_id,project_id,status,payload_json,evaluation_json,governance_json,outcome_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    record["change_id"], record["project_id"], record["status"],
                    json.dumps(record["payload"], ensure_ascii=False, sort_keys=True),
                    None, None, None, now, now,
                ),
            )
            self.conn.commit()
        return self.get(record["change_id"])

    def get(self, change_id: str) -> Optional[Dict[str, Any]]:
        self._assert_open()
        with self._lock:
            row = self.conn.execute("SELECT * FROM optimization_changes WHERE change_id=?", (str(change_id),)).fetchone()
        return self._row(row) if row else None

    def list(self, project_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        self._assert_open()
        limit = max(1, min(int(limit), 200))
        with self._lock:
            if project_id:
                rows = self.conn.execute(
                    "SELECT * FROM optimization_changes WHERE project_id=? ORDER BY created_at DESC LIMIT ?",
                    (str(project_id), limit),
                ).fetchall()
            else:
                rows = self.conn.execute(
                    "SELECT * FROM optimization_changes ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
        return [self._row(r) for r in rows]

    def update_status(self, change_id: str, status: str, *, evaluation=None, governance=None, outcome=None) -> Dict[str, Any]:
        self._assert_open()
        current = self.get(change_id)
        if not current:
            return {"status": "NOT_FOUND", "change_id": str(change_id)}
        now = _utc_now()
        with self._lock:
            self.conn.execute(
                "UPDATE optimization_changes SET status=?, evaluation_json=?, governance_json=?, outcome_json=?, updated_at=? WHERE change_id=?",
                (
                    str(status),
                    json.dumps(_json_safe(evaluation), ensure_ascii=False, sort_keys=True) if evaluation is not None else json.dumps(current["evaluation"], ensure_ascii=False, sort_keys=True) if current["evaluation"] is not None else None,
                    json.dumps(_json_safe(governance), ensure_ascii=False, sort_keys=True) if governance is not None else json.dumps(current["governance"], ensure_ascii=False, sort_keys=True) if current["governance"] is not None else None,
                    json.dumps(_json_safe(outcome), ensure_ascii=False, sort_keys=True) if outcome is not None else json.dumps(current["outcome"], ensure_ascii=False, sort_keys=True) if current["outcome"] is not None else None,
                    now,
                    str(change_id),
                ),
            )
            self.conn.commit()
        return self.get(change_id)

    @staticmethod
    def _row(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "change_id": row["change_id"],
            "project_id": row["project_id"],
            "status": row["status"],
            "payload": json.loads(row["payload_json"]),
            "evaluation": json.loads(row["evaluation_json"]) if row["evaluation_json"] else None,
            "governance": json.loads(row["governance_json"]) if row["governance_json"] else None,
            "outcome": json.loads(row["outcome_json"]) if row["outcome_json"] else None,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def close(self) -> None:
        if self._closed:
            return
        with self._lock:
            self.conn.close()
            self.conn = None
            self._closed = True
