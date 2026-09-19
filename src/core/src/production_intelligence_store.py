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


class ProductionIntelligenceStore:
    """Durable, idempotent storage for production intelligence observations/advice."""

    def __init__(self, path: str = "./data/production_intelligence.sqlite3"):
        self.path = str(path)
        if self.path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS production_observations(
                observation_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self.conn.commit()
        self._closed = False

    def _assert_open(self) -> None:
        if self._closed or self.conn is None:
            raise RuntimeError("production_intelligence_store_closed")

    def create(self, observation_id: str, project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._assert_open()
        now = _utc_now()
        safe = _json_safe(payload)
        with self._lock:
            existing = self.conn.execute("SELECT * FROM production_observations WHERE observation_id=?", (str(observation_id),)).fetchone()
            if existing:
                return self._row(existing)
            self.conn.execute(
                "INSERT INTO production_observations(observation_id,project_id,payload_json,created_at) VALUES(?,?,?,?)",
                (str(observation_id), str(project_id), json.dumps(safe, ensure_ascii=False, sort_keys=True), now),
            )
            self.conn.commit()
        return self.get(observation_id)

    def get(self, observation_id: str) -> Optional[Dict[str, Any]]:
        self._assert_open()
        with self._lock:
            row = self.conn.execute("SELECT * FROM production_observations WHERE observation_id=?", (str(observation_id),)).fetchone()
        return self._row(row) if row else None

    def list(self, project_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        self._assert_open()
        limit = max(1, min(int(limit), 200))
        with self._lock:
            if project_id:
                rows = self.conn.execute("SELECT * FROM production_observations WHERE project_id=? ORDER BY created_at DESC LIMIT ?", (str(project_id), limit)).fetchall()
            else:
                rows = self.conn.execute("SELECT * FROM production_observations ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [self._row(r) for r in rows]

    @staticmethod
    def _row(row: sqlite3.Row) -> Dict[str, Any]:
        return {"observation_id": row["observation_id"], "project_id": row["project_id"], "payload": json.loads(row["payload_json"]), "created_at": row["created_at"]}

    def close(self) -> None:
        if self._closed:
            return
        with self._lock:
            self.conn.close()
            self.conn = None
            self._closed = True
