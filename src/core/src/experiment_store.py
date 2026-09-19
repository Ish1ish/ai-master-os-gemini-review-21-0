from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
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


class ExperimentStore:
    """Durable experiment/evidence state for O42."""

    def __init__(self, path: str = "./data/experiments.sqlite3"):
        self.path = str(path)
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS experiments(
                experiment_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                run_id TEXT,
                status TEXT NOT NULL,
                decision TEXT,
                definition_json TEXT NOT NULL,
                evidence_json TEXT,
                evaluation_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.conn.commit()
        self._closed = False

    def _assert_open(self):
        if self._closed or self.conn is None:
            raise RuntimeError("experiment_store_closed")

    def create(self, definition: Dict[str, Any], project_id: str, run_id: Optional[str] = None) -> Dict[str, Any]:
        self._assert_open()
        experiment_id = str(definition.get("experiment_id") or f"EXP-{uuid.uuid4().hex[:12].upper()}")
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "experiment_id": experiment_id,
            "project_id": project_id,
            "run_id": run_id,
            "status": "READY",
            "decision": None,
            "definition": _json_safe({**definition, "experiment_id": experiment_id}),
            "evidence": None,
            "evaluation": None,
            "created_at": now,
            "updated_at": now,
        }
        with self._lock:
            self.conn.execute(
                "INSERT INTO experiments(experiment_id,project_id,run_id,status,decision,definition_json,evidence_json,evaluation_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    record["experiment_id"], record["project_id"], record["run_id"], record["status"], record["decision"],
                    json.dumps(record["definition"], ensure_ascii=False), None, None,
                    now, now,
                ),
            )
            self.conn.commit()
        return self.get(experiment_id)

    def get(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        self._assert_open()
        with self._lock:
            row = self.conn.execute("SELECT * FROM experiments WHERE experiment_id=?", (experiment_id,)).fetchone()
        if not row:
            return None
        return self._row(row)

    def list(self, project_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        self._assert_open()
        limit = max(1, min(int(limit), 200))
        with self._lock:
            if project_id:
                rows = self.conn.execute(
                    "SELECT * FROM experiments WHERE project_id=? ORDER BY created_at DESC LIMIT ?",
                    (project_id, limit),
                ).fetchall()
            else:
                rows = self.conn.execute("SELECT * FROM experiments ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [self._row(r) for r in rows]

    def save_evidence(self, experiment_id: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
        self._assert_open()
        current = self.get(experiment_id)
        if not current:
            return {"status": "NOT_FOUND", "experiment_id": experiment_id}
        merged = _json_safe(evidence)
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self.conn.execute(
                "UPDATE experiments SET status='EVIDENCE_RECORDED', evidence_json=?, updated_at=? WHERE experiment_id=?",
                (json.dumps(merged, ensure_ascii=False), now, experiment_id),
            )
            self.conn.commit()
        return self.get(experiment_id)

    def save_evaluation(self, experiment_id: str, evaluation: Dict[str, Any]) -> Dict[str, Any]:
        self._assert_open()
        current = self.get(experiment_id)
        if not current:
            return {"status": "NOT_FOUND", "experiment_id": experiment_id}
        decision = str(evaluation.get("decision") or "INCONCLUSIVE")
        status = "CONCLUDED" if decision in {"GO", "REFINE", "NO-GO"} else "INCONCLUSIVE"
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self.conn.execute(
                "UPDATE experiments SET status=?, decision=?, evaluation_json=?, updated_at=? WHERE experiment_id=?",
                (status, decision, json.dumps(_json_safe(evaluation), ensure_ascii=False), now, experiment_id),
            )
            self.conn.commit()
        return self.get(experiment_id)

    def _row(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "experiment_id": row["experiment_id"],
            "project_id": row["project_id"],
            "run_id": row["run_id"],
            "status": row["status"],
            "decision": row["decision"],
            "definition": json.loads(row["definition_json"]),
            "evidence": json.loads(row["evidence_json"]) if row["evidence_json"] else None,
            "evaluation": json.loads(row["evaluation_json"]) if row["evaluation_json"] else None,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def close(self):
        if self._closed:
            return
        with self._lock:
            if self.conn is not None:
                self.conn.close()
                self.conn = None
            self._closed = True
