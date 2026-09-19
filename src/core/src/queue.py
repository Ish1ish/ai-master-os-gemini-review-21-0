import json
import os
import sqlite3
from datetime import datetime, timezone


class DurableQueue:
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self._closed = False
        self.conn.execute("""CREATE TABLE IF NOT EXISTS queue_jobs(
            job_id TEXT PRIMARY KEY,payload TEXT NOT NULL,status TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,available_at REAL NOT NULL DEFAULT 0,
            lease_until REAL,worker_id TEXT,last_error TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)""")
        self.conn.commit()

    def _ensure_open(self):
        if self._closed:
            raise RuntimeError("DurableQueue is closed")

    def enqueue(self, job_id, payload, available_at=0.0):
        self._ensure_open()
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT OR IGNORE INTO queue_jobs(job_id,payload,status,attempts,available_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            (job_id, json.dumps(payload), "QUEUED", 0, float(available_at), now, now),
        )
        self.conn.commit()

    def claim(self, worker_id, now, lease_seconds=60):
        self._ensure_open()
        row = self.conn.execute(
            "SELECT job_id,payload,attempts FROM queue_jobs WHERE status='QUEUED' AND available_at<=? ORDER BY created_at LIMIT 1",
            (now,),
        ).fetchone()
        if not row:
            return None
        job_id, payload, attempts = row
        lease_until = now + lease_seconds
        cur = self.conn.execute(
            "UPDATE queue_jobs SET status='RUNNING',attempts=?,lease_until=?,worker_id=?,updated_at=? WHERE job_id=? AND status='QUEUED'",
            (attempts + 1, lease_until, worker_id, datetime.now(timezone.utc).isoformat(), job_id),
        )
        self.conn.commit()
        if cur.rowcount != 1:
            return None
        check = self.conn.execute("SELECT status,worker_id FROM queue_jobs WHERE job_id=?", (job_id,)).fetchone()
        return (
            {"job_id": job_id, "payload": json.loads(payload), "attempts": attempts + 1, "lease_until": lease_until}
            if check and check[0] == "RUNNING" and check[1] == worker_id
            else None
        )

    def complete(self, job_id, result):
        self._ensure_open()
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "UPDATE queue_jobs SET status='COMPLETE',payload=?,lease_until=NULL,worker_id=NULL,updated_at=? WHERE job_id=?",
            (json.dumps(result), now, job_id),
        )
        self.conn.commit()

    def fail(self, job_id, error, retry_at=None):
        self._ensure_open()
        now = datetime.now(timezone.utc).isoformat()
        if retry_at is not None:
            self.conn.execute(
                "UPDATE queue_jobs SET status='QUEUED',available_at=?,last_error=?,lease_until=NULL,worker_id=NULL,updated_at=? WHERE job_id=?",
                (float(retry_at), json.dumps(error), now, job_id),
            )
        else:
            self.conn.execute(
                "UPDATE queue_jobs SET status='FAILED',last_error=?,lease_until=NULL,worker_id=NULL,updated_at=? WHERE job_id=?",
                (json.dumps(error), now, job_id),
            )
        self.conn.commit()

    def cancel(self, job_id):
        self._ensure_open()
        now = datetime.now(timezone.utc).isoformat()
        cur = self.conn.execute(
            "UPDATE queue_jobs SET status='CANCELLED',updated_at=? WHERE job_id=? AND status='QUEUED'",
            (now, job_id),
        )
        self.conn.commit()
        return cur.rowcount == 1

    def recover_expired(self, now):
        self._ensure_open()
        now_iso = datetime.now(timezone.utc).isoformat()
        cur = self.conn.execute(
            "UPDATE queue_jobs SET status='QUEUED',lease_until=NULL,worker_id=NULL,updated_at=? WHERE status='RUNNING' AND lease_until IS NOT NULL AND lease_until<?",
            (now_iso, now),
        )
        self.conn.commit()
        return cur.rowcount

    def get(self, job_id):
        self._ensure_open()
        row = self.conn.execute(
            "SELECT job_id,payload,status,attempts,available_at,lease_until,worker_id,last_error,created_at,updated_at FROM queue_jobs WHERE job_id=?",
            (job_id,),
        ).fetchone()
        if not row:
            return None
        keys = ["job_id", "payload", "status", "attempts", "available_at", "lease_until", "worker_id", "last_error", "created_at", "updated_at"]
        d = dict(zip(keys, row))
        d["payload"] = json.loads(d["payload"])
        d["last_error"] = json.loads(d["last_error"]) if d["last_error"] else None
        return d

    def list_status(self, status):
        self._ensure_open()
        return [r[0] for r in self.conn.execute("SELECT job_id FROM queue_jobs WHERE status=? ORDER BY created_at", (status,)).fetchall()]

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.conn.close()

    def __enter__(self):
        self._ensure_open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
