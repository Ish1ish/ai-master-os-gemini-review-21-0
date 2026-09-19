from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class OutcomeIntelligenceStore:
    """Durable, idempotent persistence for outcome assessments.

    Persistence is local evidence storage only. It never executes actions,
    changes governance, or mutates O43 memory.
    """

    def __init__(self, path: str):
        self.path = str(path)
        if self.path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS outcome_intelligence_assessments(
                assessment_id TEXT PRIMARY KEY,
                trace_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_oia_project ON outcome_intelligence_assessments(project_id, created_at DESC)"
        )
        self.conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_oia_trace ON outcome_intelligence_assessments(assessment_id, trace_id)"
        )
        self.conn.commit()
        self._closed = False

    def record(self, assessment: Dict[str, Any]) -> Dict[str, Any]:
        if self._closed:
            raise RuntimeError("outcome_intelligence_store_closed")
        if not isinstance(assessment, dict):
            raise ValueError("assessment_required")
        assessment_id = str(assessment.get("assessment_id") or "").strip()
        trace_id = str(assessment.get("trace_id") or "").strip()
        project_id = str(assessment.get("project_id") or "").strip()
        if not assessment_id or not trace_id or not project_id:
            raise ValueError("assessment_id_trace_id_project_id_required")

        payload = json.dumps(assessment, ensure_ascii=False, sort_keys=True)
        existing = self.conn.execute(
            "SELECT payload_json FROM outcome_intelligence_assessments WHERE assessment_id=?",
            (assessment_id,),
        ).fetchone()
        if existing:
            if existing["payload_json"] != payload:
                raise ValueError("assessment_id_conflict")
            return {
                "status": "IDEMPOTENT_REPLAY",
                "assessment_id": assessment_id,
                "trace_id": trace_id,
            }

        self.conn.execute(
            """
            INSERT INTO outcome_intelligence_assessments(
                assessment_id,trace_id,project_id,payload_json,created_at
            ) VALUES(?,?,?,?,?)
            """,
            (assessment_id, trace_id, project_id, payload, utc_now()),
        )
        self.conn.commit()
        return {
            "status": "RECORDED",
            "assessment_id": assessment_id,
            "trace_id": trace_id,
        }

    def get(self, assessment_id: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            "SELECT payload_json FROM outcome_intelligence_assessments WHERE assessment_id=?",
            (str(assessment_id),),
        ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def list_by_project(self, project_id: str, limit: int = 20) -> list[Dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        rows = self.conn.execute(
            """
            SELECT payload_json
            FROM outcome_intelligence_assessments
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
