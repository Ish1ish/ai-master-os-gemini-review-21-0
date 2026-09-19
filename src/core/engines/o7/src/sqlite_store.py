from copy import deepcopy
from datetime import datetime, timezone
import json
import os
import sqlite3


class SQLiteMemoryStore:
    """Durable drop-in implementation of MemoryStore."""

    def __init__(self, path):
        self.path = str(path)
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_objects(
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                object_id TEXT NOT NULL,
                version TEXT NOT NULL,
                project_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(object_id, version)
            )
        """)
        self.conn.commit()
        self._closed = False

    def write(self, obj):
        if self._closed or self.conn is None:
            raise RuntimeError("memory_store_closed")
        required = ["object_type", "object_id", "version", "project_id", "summary", "scope", "confidence"]
        missing = [k for k in required if k not in obj]
        if missing:
            raise ValueError(f"missing memory fields: {missing}")
        obj = deepcopy(obj)
        obj.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        obj.setdefault("status", "active")
        obj.setdefault("source_refs", [])
        obj.setdefault("supersedes", None)
        latest = self.latest(obj["object_id"])
        if latest is not None and obj["version"] == latest["version"]:
            comparable_new = dict(obj)
            comparable_existing = dict(latest)
            comparable_new.pop("created_at", None)
            comparable_existing.pop("created_at", None)
            if comparable_new == comparable_existing:
                return deepcopy(latest)
            raise ValueError("memory version conflict")
        if latest is not None:
            obj.setdefault("supersedes", f'{latest["object_id"]}:{latest["version"]}')
        else:
            obj.setdefault("supersedes", None)
        self.conn.execute(
            "INSERT INTO memory_objects(object_id,version,project_id,payload,created_at) VALUES(?,?,?,?,?)",
            (obj["object_id"], obj["version"], obj["project_id"], json.dumps(obj, ensure_ascii=False), obj["created_at"]),
        )
        self.conn.commit()
        return deepcopy(obj)

    def latest(self, object_id):
        if self._closed or self.conn is None:
            return None
        row = self.conn.execute(
            "SELECT payload FROM memory_objects WHERE object_id=? ORDER BY row_id DESC LIMIT 1",
            (object_id,),
        ).fetchone()
        return json.loads(row[0]) if row else None

    def history(self, object_id):
        if self._closed or self.conn is None:
            return []
        rows = self.conn.execute(
            "SELECT payload FROM memory_objects WHERE object_id=? ORDER BY row_id",
            (object_id,),
        ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def list_by_project(self, project_id, limit=100):
        if self._closed or self.conn is None:
            return []
        limit=max(1, min(int(limit), 500))
        rows=self.conn.execute(
            "SELECT payload FROM memory_objects WHERE project_id=? ORDER BY row_id DESC LIMIT ?",
            (str(project_id), limit),
        ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def close(self):
        conn = getattr(self, "conn", None)
        if conn is not None:
            conn.close()
            self.conn = None
        self._closed = True
