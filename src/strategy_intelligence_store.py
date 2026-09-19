from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StrategyIntelligenceStore:
    def __init__(self, path: str):
        self.path = str(path)
        if self.path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS strategy_intelligence(
                analysis_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_si_project ON strategy_intelligence(project_id, created_at DESC)"
        )
        self.conn.commit()
        self._closed = False

    def record(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        if self._closed:
            raise RuntimeError("strategy_intelligence_store_closed")
        aid = str(analysis.get("analysis_id") or "")
        project_id = str(analysis.get("project_id") or "")
        if not aid or not project_id:
            raise ValueError("analysis_id_project_id_required")

        payload = json.dumps(analysis, ensure_ascii=False, sort_keys=True)
        row = self.conn.execute(
            "SELECT payload_json FROM strategy_intelligence WHERE analysis_id=?",
            (aid,),
        ).fetchone()

        if row:
            if row["payload_json"] != payload:
                raise ValueError("analysis_id_conflict")
            return {"status": "IDEMPOTENT_REPLAY", "analysis_id": aid}

        self.conn.execute(
            "INSERT INTO strategy_intelligence(analysis_id,project_id,payload_json,created_at) VALUES(?,?,?,?)",
            (aid, project_id, payload, utc_now()),
        )
        self.conn.commit()
        return {"status": "RECORDED", "analysis_id": aid}

    def get(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            "SELECT payload_json FROM strategy_intelligence WHERE analysis_id=?",
            (str(analysis_id),),
        ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def close(self) -> None:
        if not self._closed:
            self.conn.close()
            self._closed = True
