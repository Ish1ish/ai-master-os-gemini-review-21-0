import json
import os
import sqlite3
from datetime import datetime, timezone


class DeadLetterStore:
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self._closed = False
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS dead_letters(job_id TEXT PRIMARY KEY,payload TEXT NOT NULL,error TEXT NOT NULL,attempts INTEGER NOT NULL,created_at TEXT NOT NULL)"
        )
        self.conn.commit()

    def _ensure_open(self):
        if self._closed:
            raise RuntimeError("DeadLetterStore is closed")

    def put(self, job_id, payload, error, attempts):
        self._ensure_open()
        self.conn.execute(
            "INSERT OR REPLACE INTO dead_letters(job_id,payload,error,attempts,created_at) VALUES(?,?,?,?,?)",
            (job_id, json.dumps(payload), json.dumps(error), attempts, datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()

    def get(self, job_id):
        self._ensure_open()
        row = self.conn.execute("SELECT job_id,payload,error,attempts,created_at FROM dead_letters WHERE job_id=?", (job_id,)).fetchone()
        if not row:
            return None
        return {"job_id": row[0], "payload": json.loads(row[1]), "error": json.loads(row[2]), "attempts": row[3], "created_at": row[4]}

    def list_all(self):
        self._ensure_open()
        return [r[0] for r in self.conn.execute("SELECT job_id FROM dead_letters ORDER BY created_at").fetchall()]

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
