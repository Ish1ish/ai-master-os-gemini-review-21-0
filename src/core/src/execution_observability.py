from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional


SCHEMA_VERSION = "EOE-v1.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def trace_id(*, project_id: str, run_id: Optional[str], decision_plan_id: str,
             intent_id: str, execution_id: Optional[str] = None) -> str:
    seed = {
        "project_id": project_id,
        "run_id": run_id,
        "decision_plan_id": decision_plan_id,
        "intent_id": intent_id,
    }
    return "TRC-" + sha256_json(seed)[:24].upper()


class ExecutionObservabilityStore:
    """Durable decision -> intent -> execution -> outcome evidence trace."""

    EVENT_TYPES = {
        "DECISION_RECORDED",
        "INTENT_RECORDED",
        "GOVERNANCE_RECORDED",
        "EXECUTION_SUBMITTED",
        "EXECUTION_STARTED",
        "EXECUTION_FINISHED",
        "OUTCOME_RECORDED",
        "OBSERVATION_FAILED",
    }

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.RLock()
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS execution_observability_traces(
                trace_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                run_id TEXT,
                decision_plan_id TEXT NOT NULL,
                intent_id TEXT NOT NULL,
                execution_id TEXT,
                decision_status TEXT,
                execution_state TEXT,
                outcome_status TEXT,
                expected_action TEXT,
                actual_result_hash TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS execution_observability_events(
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                decision_plan_id TEXT NOT NULL,
                intent_id TEXT NOT NULL,
                execution_id TEXT,
                status TEXT,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS execution_outcome_evidence(
                evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT NOT NULL,
                evidence_key TEXT NOT NULL UNIQUE,
                project_id TEXT NOT NULL,
                run_id TEXT,
                decision_plan_id TEXT NOT NULL,
                intent_id TEXT NOT NULL,
                execution_id TEXT,
                expected_status TEXT NOT NULL,
                actual_status TEXT NOT NULL,
                outcome_status TEXT NOT NULL,
                success INTEGER NOT NULL,
                evidence_refs_json TEXT NOT NULL,
                result_json TEXT,
                error_json TEXT,
                duration_ms REAL,
                created_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_eo_trace_events ON execution_observability_events(trace_id, event_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_eo_project ON execution_observability_traces(project_id, created_at)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_eo_outcome_trace ON execution_outcome_evidence(trace_id, evidence_id)")
        self.conn.commit()

    def _ensure_trace(self, *, project_id: str, run_id: Optional[str], decision_plan_id: str,
                      intent_id: str, execution_id: Optional[str]) -> str:
        tid = trace_id(
            project_id=project_id,
            run_id=run_id,
            decision_plan_id=decision_plan_id,
            intent_id=intent_id,
            execution_id=execution_id,
        )
        now = utc_now()
        self.conn.execute(
            """
            INSERT INTO execution_observability_traces(
                trace_id,project_id,run_id,decision_plan_id,intent_id,execution_id,
                created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(trace_id) DO UPDATE SET
                execution_id=COALESCE(execution_observability_traces.execution_id, excluded.execution_id),
                updated_at=excluded.updated_at
            """,
            (tid, project_id, run_id, decision_plan_id, intent_id, execution_id, now, now),
        )
        return tid

    def record_event(self, *, project_id: str, run_id: Optional[str], decision_plan_id: str,
                     intent_id: str, execution_id: Optional[str], event_type: str,
                     status: Optional[str], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if event_type not in self.EVENT_TYPES:
            raise ValueError("invalid_observability_event_type")
        with self._lock:
            tid = self._ensure_trace(
                project_id=project_id, run_id=run_id, decision_plan_id=decision_plan_id,
                intent_id=intent_id, execution_id=execution_id,
            )
            now = utc_now()
            self.conn.execute(
                """
                INSERT INTO execution_observability_events(
                    trace_id,event_type,decision_plan_id,intent_id,execution_id,status,metadata_json,created_at
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (tid, event_type, decision_plan_id, intent_id, execution_id, status, canonical_json(metadata or {}), now),
            )
            updates = {"updated_at": now}
            if event_type == "DECISION_RECORDED":
                updates["decision_status"] = status
                updates["expected_action"] = (metadata or {}).get("action")
            elif event_type == "EXECUTION_SUBMITTED":
                updates["execution_state"] = status
            elif event_type == "EXECUTION_STARTED":
                updates["execution_state"] = status
            elif event_type == "EXECUTION_FINISHED":
                updates["execution_state"] = status
                result = (metadata or {}).get("result")
                if result is not None:
                    updates["actual_result_hash"] = sha256_json(result)
            elif event_type == "OUTCOME_RECORDED":
                updates["outcome_status"] = status
            assignments = []
            values = []
            for key, value in updates.items():
                assignments.append(f"{key}=?")
                values.append(value)
            values.append(tid)
            self.conn.execute(
                f"UPDATE execution_observability_traces SET {','.join(assignments)} WHERE trace_id=?",
                tuple(values),
            )
            self.conn.commit()
            return {"trace_id": tid, "event_type": event_type, "status": status}

    def record_outcome(self, *, project_id: str, run_id: Optional[str], decision_plan_id: str,
                       intent_id: str, execution_id: Optional[str], expected_status: str,
                       actual_status: str, outcome_status: str, success: bool,
                       evidence_refs: Optional[list[str]] = None, result: Any = None,
                       error: Any = None, duration_ms: Optional[float] = None,
                       evidence_key: Optional[str] = None) -> Dict[str, Any]:
        refs = list(evidence_refs or [])
        key_seed = {
            "trace": trace_id(project_id=project_id, run_id=run_id, decision_plan_id=decision_plan_id, intent_id=intent_id, execution_id=execution_id),
            "expected_status": expected_status,
            "actual_status": actual_status,
            "outcome_status": outcome_status,
            "success": bool(success),
            "evidence_refs": refs,
            "result": result,
            "error": error,
        }
        key = evidence_key or ("OE-" + sha256_json(key_seed)[:32].upper())
        with self._lock:
            tid = self._ensure_trace(
                project_id=project_id, run_id=run_id, decision_plan_id=decision_plan_id,
                intent_id=intent_id, execution_id=execution_id,
            )
            try:
                self.conn.execute(
                    """
                    INSERT INTO execution_outcome_evidence(
                        trace_id,evidence_key,project_id,run_id,decision_plan_id,intent_id,execution_id,
                        expected_status,actual_status,outcome_status,success,evidence_refs_json,
                        result_json,error_json,duration_ms,created_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        tid, key, project_id, run_id, decision_plan_id, intent_id, execution_id,
                        expected_status, actual_status, outcome_status, int(bool(success)), canonical_json(refs),
                        canonical_json(result) if result is not None else None,
                        canonical_json(error) if error is not None else None,
                        duration_ms, utc_now(),
                    ),
                )
            except sqlite3.IntegrityError:
                existing = self.conn.execute(
                    "SELECT evidence_id FROM execution_outcome_evidence WHERE evidence_key=?", (key,)
                ).fetchone()
                self.conn.rollback()
                if existing:
                    return {"status": "IDEMPOTENT_REPLAY", "evidence_id": existing[0], "trace_id": tid, "evidence_key": key}
                raise
            self.conn.commit()
            self.record_event(
                project_id=project_id, run_id=run_id, decision_plan_id=decision_plan_id,
                intent_id=intent_id, execution_id=execution_id, event_type="OUTCOME_RECORDED",
                status=outcome_status,
                metadata={"success": bool(success), "evidence_key": key, "evidence_refs": refs, "duration_ms": duration_ms},
            )
            return {"status": "RECORDED", "trace_id": tid, "evidence_key": key}

    def trace(self, trace: str) -> Dict[str, Any]:
        with self._lock:
            row = self.conn.execute(
                "SELECT trace_id,project_id,run_id,decision_plan_id,intent_id,execution_id,decision_status,execution_state,outcome_status,expected_action,actual_result_hash,created_at,updated_at FROM execution_observability_traces WHERE trace_id=?",
                (trace,),
            ).fetchone()
            if not row:
                raise KeyError("observability_trace_not_found")
            events = self.conn.execute(
                "SELECT event_id,event_type,status,metadata_json,created_at FROM execution_observability_events WHERE trace_id=? ORDER BY event_id",
                (trace,),
            ).fetchall()
            outcomes = self.conn.execute(
                "SELECT evidence_id,evidence_key,expected_status,actual_status,outcome_status,success,evidence_refs_json,result_json,error_json,duration_ms,created_at FROM execution_outcome_evidence WHERE trace_id=? ORDER BY evidence_id",
                (trace,),
            ).fetchall()
        return {
            "trace_id": row[0], "project_id": row[1], "run_id": row[2],
            "decision_plan_id": row[3], "intent_id": row[4], "execution_id": row[5],
            "decision_status": row[6], "execution_state": row[7], "outcome_status": row[8],
            "expected_action": row[9], "actual_result_hash": row[10],
            "created_at": row[11], "updated_at": row[12],
            "events": [
                {"event_id": x[0], "event_type": x[1], "status": x[2], "metadata": json.loads(x[3] or "{}"), "created_at": x[4]}
                for x in events
            ],
            "outcomes": [
                {
                    "evidence_id": x[0], "evidence_key": x[1], "expected_status": x[2],
                    "actual_status": x[3], "outcome_status": x[4], "success": bool(x[5]),
                    "evidence_refs": json.loads(x[6] or "[]"),
                    "result": json.loads(x[7]) if x[7] else None,
                    "error": json.loads(x[8]) if x[8] else None,
                    "duration_ms": x[9], "created_at": x[10],
                }
                for x in outcomes
            ],
        }

    def trace_for_intent(self, intent_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self.conn.execute(
                "SELECT trace_id FROM execution_observability_traces WHERE intent_id=? ORDER BY updated_at DESC LIMIT 1",
                (intent_id,),
            ).fetchone()
        return self.trace(row[0]) if row else None

    def close(self) -> None:
        with self._lock:
            if getattr(self, "conn", None) is not None:
                self.conn.close()
                self.conn = None


class ExecutionObservability:
    """High-level, side-effect-free analytics adapter around the durable store."""

    def __init__(self, store: ExecutionObservabilityStore):
        self.store = store

    def record_decision(self, *, project_id, run_id, decision_plan_id, intent_id, status, action, decision_basis=None, evidence_refs=None):
        return self.store.record_event(
            project_id=project_id, run_id=run_id, decision_plan_id=decision_plan_id, intent_id=intent_id,
            execution_id=None, event_type="DECISION_RECORDED", status=status,
            metadata={"action": action, "decision_basis": decision_basis or {}, "evidence_refs": evidence_refs or []},
        )

    def record_intent(self, *, project_id, run_id, decision_plan_id, intent_id, status, intent_fingerprint_value):
        return self.store.record_event(
            project_id=project_id, run_id=run_id, decision_plan_id=decision_plan_id, intent_id=intent_id,
            execution_id=None, event_type="INTENT_RECORDED", status=status,
            metadata={"intent_fingerprint": intent_fingerprint_value},
        )

    def record_execution(self, *, project_id, run_id, decision_plan_id, intent_id, execution_id, state, phase):
        event_type = "EXECUTION_STARTED" if phase == "started" else "EXECUTION_FINISHED" if phase == "finished" else "EXECUTION_SUBMITTED"
        return self.store.record_event(
            project_id=project_id, run_id=run_id, decision_plan_id=decision_plan_id, intent_id=intent_id,
            execution_id=execution_id, event_type=event_type, status=state,
        )

    def record_outcome(self, **kwargs):
        return self.store.record_outcome(**kwargs)

    def for_intent(self, intent_id: str):
        return self.store.trace_for_intent(intent_id)

    def close(self):
        self.store.close()
