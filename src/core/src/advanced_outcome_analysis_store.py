from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AdvancedOutcomeAnalysisStore:
    """Durable local storage for v1.6 aggregate analyses only."""

    def __init__(self, path: str):
        self.path = str(path)
        if self.path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS advanced_outcome_analyses(
                analysis_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_aoa_project ON advanced_outcome_analyses(project_id, created_at DESC)"
        )
        self.conn.commit()
        self._closed = False

    def record(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        if self._closed:
            raise RuntimeError("advanced_outcome_analysis_store_closed")
        if not isinstance(analysis, dict):
            raise ValueError("analysis_required")

        analysis_id = str(analysis.get("analysis_id") or "").strip()
        project_id = str(analysis.get("project_id") or "").strip()
        if not analysis_id or not project_id:
            raise ValueError("analysis_id_project_id_required")

        payload = json.dumps(analysis, ensure_ascii=False, sort_keys=True)
        row = self.conn.execute(
            "SELECT payload_json FROM advanced_outcome_analyses WHERE analysis_id=?",
            (analysis_id,),
        ).fetchone()
        if row:
            if row["payload_json"] != payload:
                raise ValueError("analysis_id_conflict")
            return {"status": "IDEMPOTENT_REPLAY", "analysis_id": analysis_id, "project_id": project_id}

        self.conn.execute(
            "INSERT INTO advanced_outcome_analyses(analysis_id,project_id,payload_json,created_at) VALUES(?,?,?,?)",
            (analysis_id, project_id, payload, utc_now()),
        )
        self.conn.commit()
        return {"status": "RECORDED", "analysis_id": analysis_id, "project_id": project_id}

    def get(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            "SELECT payload_json FROM advanced_outcome_analyses WHERE analysis_id=?",
            (str(analysis_id),),
        ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def list_by_project(self, project_id: str, limit: int = 20) -> list[Dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        rows = self.conn.execute(
            """
            SELECT payload_json
            FROM advanced_outcome_analyses
            WHERE project_id=?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (str(project_id), limit),
        ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def close(self) -> None:
        if not self._closed:
            self.conn.close()
            self._closed = True
