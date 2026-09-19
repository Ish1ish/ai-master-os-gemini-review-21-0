from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def plan_hash(plan: Dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(plan).encode("utf-8")).hexdigest()


CYCLE_STATES = {
    "RECEIVED", "RUNNING", "WAITING_HUMAN_APPROVAL", "BLOCKED",
    "EVIDENCE_PENDING", "LEARNING", "COMPLETE", "RECOVERY_REQUIRED",
    "FAILED",
}


class CycleStore:
    """Durable O46 cycle state + append-only lifecycle events."""

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.RLock()
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cycles(
                cycle_id TEXT PRIMARY KEY,
                idempotency_key TEXT NOT NULL UNIQUE,
                project_id TEXT NOT NULL,
                run_id TEXT,
                requested_by TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                plan_hash TEXT NOT NULL,
                execution_ids_json TEXT NOT NULL,
                experiment_id TEXT,
                state TEXT NOT NULL,
                result_json TEXT,
                error_json TEXT,
                next_cycle_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cycle_events(
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                from_state TEXT,
                to_state TEXT,
                metadata_json TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_cycle_project ON cycles(project_id, created_at)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_cycle_events ON cycle_events(cycle_id, event_id)")
        self.conn.commit()

    def _row(self, row: Optional[tuple]) -> Optional[Dict[str, Any]]:
        if not row:
            return None
        keys = [
            "cycle_id", "idempotency_key", "project_id", "run_id", "requested_by",
            "plan_json", "plan_hash", "execution_ids_json", "experiment_id", "state",
            "result_json", "error_json", "next_cycle_json", "created_at", "updated_at",
        ]
        d = dict(zip(keys, row))
        d["plan"] = json.loads(d.pop("plan_json"))
        d["execution_ids"] = json.loads(d.pop("execution_ids_json"))
        d["result"] = json.loads(d["result_json"]) if d["result_json"] else None
        d["error"] = json.loads(d["error_json"]) if d["error_json"] else None
        d["next_cycle"] = json.loads(d["next_cycle_json"]) if d["next_cycle_json"] else None
        d.pop("result_json", None)
        d.pop("error_json", None)
        d.pop("next_cycle_json", None)
        return d

    def get(self, cycle_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self.conn.execute("SELECT * FROM cycles WHERE cycle_id=?", (cycle_id,)).fetchone()
        return self._row(row)

    def by_idempotency(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self.conn.execute("SELECT * FROM cycles WHERE idempotency_key=?", (key,)).fetchone()
        return self._row(row)

    def create(self, *, idempotency_key: str, project_id: str, run_id: Optional[str], requested_by: str,
               plan: Dict[str, Any], execution_ids: list[str], experiment_id: Optional[str]) -> Dict[str, Any]:
        existing = self.by_idempotency(idempotency_key)
        digest = plan_hash(plan)
        if existing:
            if existing["plan_hash"] != digest:
                raise ValueError("cycle_idempotency_conflict")
            return existing
        cycle_id = "CYC-" + uuid.uuid4().hex[:16].upper()
        now = utc_now()
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO cycles(
                    cycle_id,idempotency_key,project_id,run_id,requested_by,plan_json,plan_hash,
                    execution_ids_json,experiment_id,state,result_json,error_json,next_cycle_json,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    cycle_id, idempotency_key, project_id, run_id, requested_by,
                    canonical_json(plan), digest, canonical_json(execution_ids), experiment_id,
                    "RECEIVED", None, None, None, now, now,
                ),
            )
            self._event_unlocked(cycle_id, "CREATED", None, "RECEIVED", {"plan_hash": digest})
            self.conn.commit()
        return self.get(cycle_id)

    def _event_unlocked(self, cycle_id: str, event_type: str, from_state: Optional[str],
                        to_state: Optional[str], metadata: Optional[Dict[str, Any]] = None) -> None:
        self.conn.execute(
            "INSERT INTO cycle_events(cycle_id,event_type,from_state,to_state,metadata_json,created_at) VALUES(?,?,?,?,?,?)",
            (cycle_id, event_type, from_state, to_state, canonical_json(metadata or {}), utc_now()),
        )

    def events(self, cycle_id: str) -> list[Dict[str, Any]]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT event_id,event_type,from_state,to_state,metadata_json,created_at FROM cycle_events WHERE cycle_id=? ORDER BY event_id",
                (cycle_id,),
            ).fetchall()
        return [
            {"event_id": r[0], "event_type": r[1], "from_state": r[2], "to_state": r[3],
             "metadata": json.loads(r[4] or "{}"), "created_at": r[5]}
            for r in rows
        ]

    def transition(self, cycle_id: str, state: str, *, result: Any = None,
                   error: Any = None, next_cycle: Any = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if state not in CYCLE_STATES:
            raise ValueError("invalid_cycle_state")
        with self._lock:
            row = self.conn.execute("SELECT state FROM cycles WHERE cycle_id=?", (cycle_id,)).fetchone()
            if not row:
                raise KeyError("cycle_not_found")
            previous = row[0]
            now = utc_now()
            self.conn.execute(
                "UPDATE cycles SET state=?, result_json=?, error_json=?, next_cycle_json=?, updated_at=? WHERE cycle_id=?",
                (
                    state,
                    canonical_json(result) if result is not None else None,
                    canonical_json(error) if error is not None else None,
                    canonical_json(next_cycle) if next_cycle is not None else None,
                    now,
                    cycle_id,
                ),
            )
            self._event_unlocked(cycle_id, "STATE_CHANGED", previous, state, metadata)
            self.conn.commit()
        return self.get(cycle_id)

    def close(self) -> None:
        with self._lock:
            if getattr(self, "conn", None) is not None:
                self.conn.close()
                self.conn = None
