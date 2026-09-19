from __future__ import annotations
import hashlib, json, os, sqlite3, threading, uuid, time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

EXECUTION_STATES = {
    "PENDING_GOVERNANCE","AWAITING_APPROVAL","READY","RUNNING",
    "SUCCEEDED","FAILED_RETRYABLE","FAILED_TERMINAL","BLOCKED",
    "CANCELLED","RECOVERY_REQUIRED",
}

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

class ExecutionReceiptStore:
    """Durable execution receipts, idempotency, leases, recovery and audit events."""
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.RLock()
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS execution_receipts(
                execution_id TEXT PRIMARY KEY,
                idempotency_key TEXT NOT NULL UNIQUE,
                project_id TEXT NOT NULL,
                run_id TEXT,
                action TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                tool_version TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                request_hash TEXT NOT NULL,
                governance_decision_id TEXT,
                approval_id TEXT,
                requested_by TEXT NOT NULL,
                state TEXT NOT NULL,
                attempt INTEGER NOT NULL DEFAULT 0,
                lease_until REAL,
                worker_id TEXT,
                result_json TEXT,
                error_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS execution_events(
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                from_state TEXT,
                to_state TEXT,
                worker_id TEXT,
                metadata_json TEXT,
                created_at TEXT NOT NULL
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_execution_project ON execution_receipts(project_id, created_at)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_execution_run ON execution_receipts(run_id, created_at)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_execution_events ON execution_events(execution_id, event_id)")
        self.conn.commit()

    def _row(self, row) -> Optional[Dict[str, Any]]:
        if not row:
            return None
        keys = [
            "execution_id","idempotency_key","project_id","run_id","action","tool_name",
            "tool_version","payload_json","payload_hash","request_hash",
            "governance_decision_id","approval_id","requested_by","state","attempt",
            "lease_until","worker_id","result_json","error_json","created_at",
            "updated_at","started_at","finished_at",
        ]
        d = dict(zip(keys, row))
        d["payload"] = json.loads(d.pop("payload_json"))
        d["result"] = json.loads(d["result_json"]) if d["result_json"] else None
        d["error"] = json.loads(d["error_json"]) if d["error_json"] else None
        d.pop("result_json", None)
        d.pop("error_json", None)
        return d

    def _event_unlocked(self, execution_id, event_type, from_state=None, to_state=None,
                        worker_id=None, metadata=None):
        self.conn.execute(
            """INSERT INTO execution_events(
                execution_id,event_type,from_state,to_state,worker_id,metadata_json,created_at
            ) VALUES(?,?,?,?,?,?,?)""",
            (
                execution_id, event_type, from_state, to_state, worker_id,
                json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True), utc_now()
            ),
        )

    def event(self, execution_id, event_type, *, from_state=None, to_state=None,
              worker_id=None, metadata=None):
        with self._lock:
            self._event_unlocked(execution_id, event_type, from_state, to_state, worker_id, metadata)
            self.conn.commit()

    def events(self, execution_id):
        with self._lock:
            rows = self.conn.execute(
                """SELECT event_id,event_type,from_state,to_state,worker_id,metadata_json,created_at
                   FROM execution_events WHERE execution_id=? ORDER BY event_id""",
                (execution_id,)
            ).fetchall()
        return [
            {"event_id":r[0],"event_type":r[1],"from_state":r[2],"to_state":r[3],
             "worker_id":r[4],"metadata":json.loads(r[5] or "{}"),"created_at":r[6]}
            for r in rows
        ]

    def get(self, execution_id):
        with self._lock:
            row = self.conn.execute("SELECT * FROM execution_receipts WHERE execution_id=?", (execution_id,)).fetchone()
        return self._row(row)

    def by_idempotency(self, idempotency_key):
        with self._lock:
            row = self.conn.execute("SELECT * FROM execution_receipts WHERE idempotency_key=?", (idempotency_key,)).fetchone()
        return self._row(row)

    def create(self, *, idempotency_key, project_id, run_id, action, tool_name, tool_version,
               payload, request_hash, governance_decision_id, approval_id, requested_by, state):
        if state not in EXECUTION_STATES:
            raise ValueError("invalid_execution_state")
        now = utc_now()
        execution_id = "EXE-" + uuid.uuid4().hex[:16].upper()
        payload_json = canonical_json(payload)
        payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        with self._lock:
            try:
                self.conn.execute("""
                    INSERT INTO execution_receipts(
                        execution_id,idempotency_key,project_id,run_id,action,tool_name,
                        tool_version,payload_json,payload_hash,request_hash,
                        governance_decision_id,approval_id,requested_by,state,attempt,
                        lease_until,worker_id,result_json,error_json,created_at,updated_at,
                        started_at,finished_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,NULL,NULL,NULL,NULL,?,?,NULL,NULL)
                """, (
                    execution_id,idempotency_key,project_id,run_id,action,tool_name,
                    tool_version,payload_json,payload_hash,request_hash,
                    governance_decision_id,approval_id,requested_by,state,now,now
                ))
                self._event_unlocked(execution_id, "CREATED", to_state=state, metadata={"request_hash":request_hash})
                self.conn.commit()
            except sqlite3.IntegrityError:
                self.conn.rollback()
                existing = self.by_idempotency(idempotency_key)
                if existing:
                    return existing
                raise
        return self.get(execution_id)

    def update_state(self, execution_id, state, *, result=None, error=None, now=None):
        if state not in EXECUTION_STATES:
            raise ValueError("invalid_execution_state")
        now = now or utc_now()
        with self._lock:
            current = self.conn.execute(
                "SELECT state FROM execution_receipts WHERE execution_id=?", (execution_id,)
            ).fetchone()
            if not current:
                raise KeyError("execution_not_found")
            previous = current[0]
            self.conn.execute("""
                UPDATE execution_receipts
                SET state=?, result_json=?, error_json=?, updated_at=?,
                    finished_at=CASE
                        WHEN ? IN ('SUCCEEDED','FAILED_RETRYABLE','FAILED_TERMINAL','BLOCKED','CANCELLED')
                        THEN COALESCE(finished_at, ?) ELSE finished_at END
                WHERE execution_id=?
            """, (
                state,
                json.dumps(result, ensure_ascii=False, sort_keys=True) if result is not None else None,
                json.dumps(error, ensure_ascii=False, sort_keys=True) if error is not None else None,
                now, state, now, execution_id
            ))
            self._event_unlocked(execution_id, "STATE_CHANGED", from_state=previous, to_state=state,
                                 metadata={"has_result": result is not None, "has_error": error is not None})
            self.conn.commit()
        item = self.get(execution_id)
        if not item:
            raise KeyError("execution_not_found")
        return item

    def claim(self, execution_id, worker_id, lease_seconds=60, now_epoch=None):
        now_epoch = time.time() if now_epoch is None else float(now_epoch)
        lease_until = now_epoch + max(1, int(lease_seconds))
        now = utc_now()
        with self._lock:
            try:
                self.conn.execute("BEGIN IMMEDIATE")
                row = self.conn.execute(
                    "SELECT state,attempt FROM execution_receipts WHERE execution_id=?", (execution_id,)
                ).fetchone()
                if not row or row[0] != "READY":
                    self.conn.rollback()
                    return None
                attempt = int(row[1]) + 1
                self.conn.execute("""
                    UPDATE execution_receipts
                    SET state='RUNNING', attempt=?, lease_until=?, worker_id=?,
                        started_at=COALESCE(started_at, ?), updated_at=?
                    WHERE execution_id=? AND state='READY'
                """, (attempt,lease_until,worker_id,now,now,execution_id))
                if self.conn.execute("SELECT changes()").fetchone()[0] != 1:
                    self.conn.rollback()
                    return None
                self._event_unlocked(execution_id, "CLAIMED", from_state="READY", to_state="RUNNING",
                                     worker_id=worker_id, metadata={"lease_until":lease_until,"attempt":attempt})
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise
        return self.get(execution_id)

    def recover_expired(self, now_epoch=None):
        now_epoch = time.time() if now_epoch is None else float(now_epoch)
        now = utc_now()
        with self._lock:
            rows = self.conn.execute("""
                SELECT execution_id FROM execution_receipts
                WHERE state='RUNNING' AND lease_until IS NOT NULL AND lease_until < ?
            """, (now_epoch,)).fetchall()
            for (execution_id,) in rows:
                self.conn.execute("""
                    UPDATE execution_receipts
                    SET state='RECOVERY_REQUIRED', lease_until=NULL, worker_id=NULL, updated_at=?,
                        error_json=?
                    WHERE execution_id=? AND state='RUNNING'
                """, (
                    now,
                    json.dumps({"code":"execution_lease_expired",
                                "message":"External outcome may be unknown; reconciliation is required before retry."}),
                    execution_id
                ))
                self._event_unlocked(execution_id, "LEASE_EXPIRED", from_state="RUNNING",
                                     to_state="RECOVERY_REQUIRED", metadata={"reason":"execution_lease_expired"})
            self.conn.commit()
        return [self.get(x[0]) for x in rows]

    def mark_ready(self, execution_id):
        return self.update_state(execution_id, "READY")

    def retry(self, execution_id):
        item = self.get(execution_id)
        if not item:
            return {"status":"NOT_FOUND","execution_id":execution_id}
        if item["state"] != "FAILED_RETRYABLE":
            return {"status":"CONFLICT","state":item["state"],"execution_id":execution_id}
        return self.update_state(execution_id, "READY", error=None)

    def cancel(self, execution_id):
        item = self.get(execution_id)
        if not item:
            return {"status":"NOT_FOUND","execution_id":execution_id}
        if item["state"] not in {"PENDING_GOVERNANCE","AWAITING_APPROVAL","READY"}:
            return {"status":"CONFLICT","state":item["state"],"execution_id":execution_id}
        return self.update_state(execution_id,"CANCELLED",error={"code":"cancelled_before_execution"})

    def list(self, project_id=None, run_id=None, states=None, limit=100):
        clauses=["1=1"]; params=[]
        if project_id: clauses.append("project_id=?"); params.append(project_id)
        if run_id: clauses.append("run_id=?"); params.append(run_id)
        if states:
            ph=",".join("?" for _ in states); clauses.append(f"state IN ({ph})"); params.extend(states)
        params.append(max(1,min(int(limit),500)))
        with self._lock:
            ids=[r[0] for r in self.conn.execute(
                "SELECT execution_id FROM execution_receipts WHERE "+" AND ".join(clauses)+" ORDER BY created_at DESC LIMIT ?", tuple(params)
            ).fetchall()]
        return [self.get(x) for x in ids]

    def close(self):
        with self._lock:
            conn=getattr(self,"conn",None)
            if conn is not None:
                conn.close()
                self.conn=None
