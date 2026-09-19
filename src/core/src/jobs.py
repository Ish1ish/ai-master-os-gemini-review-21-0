import sqlite3
import os
import json
import threading
from datetime import datetime, timezone


def _json_safe(value):
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _parent(path):
    p=os.path.dirname(os.path.abspath(path))
    os.makedirs(p, exist_ok=True)


def normalize_constraints(value):
    """Normalize a run constraint field into a stable list without iterating strings character-by-character."""
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return lines or [text]
    if isinstance(value, (list, tuple, set)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value).strip()] if str(value).strip() else []


class JobStore:
    def __init__(self, path):
        self.path=path
        _parent(path)
        self.conn=sqlite3.connect(path, check_same_thread=False, timeout=30)
        self._lock=threading.RLock()
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs(
                job_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                request TEXT NOT NULL,
                status TEXT NOT NULL,
                result_json TEXT,
                error_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                context_json TEXT
            )
        """)
        columns={row[1] for row in self.conn.execute("PRAGMA table_info(jobs)").fetchall()}
        if "context_json" not in columns:
            self.conn.execute("ALTER TABLE jobs ADD COLUMN context_json TEXT")
        self.conn.commit()

    @staticmethod
    def _context(audience=None, goal=None, constraints=None, language="en"):
        return {
            "audience": audience or "small businesses using AI tools",
            "goal": goal or "validate a lean business opportunity",
            "constraints": normalize_constraints(constraints),
            "language": (language or "en").lower(),
        }

    def create(self, job_id, project_id, request, audience=None, goal=None, constraints=None, language="en"):
        now=datetime.now(timezone.utc).isoformat()
        context=json.dumps(self._context(audience, goal, constraints, language), ensure_ascii=False)
        with self._lock:
            self.conn.execute(
                "INSERT INTO jobs(job_id,project_id,request,status,created_at,updated_at,context_json) VALUES(?,?,?,?,?,?,?)",
                (job_id,project_id,request,"QUEUED",now,now,context)
            )
            self.conn.commit()

    def claim(self, job_id):
        """Atomically move QUEUED -> RUNNING; return None when another executor owns it."""
        now=datetime.now(timezone.utc).isoformat()
        with self._lock:
            try:
                self.conn.execute("BEGIN IMMEDIATE")
                row=self.conn.execute("SELECT status FROM jobs WHERE job_id=?",(job_id,)).fetchone()
                if not row or row[0] != "QUEUED":
                    self.conn.rollback()
                    return None
                self.conn.execute(
                    "UPDATE jobs SET status=?, result_json=NULL, error_json=NULL, updated_at=? WHERE job_id=? AND status='QUEUED'",
                    ("RUNNING",now,job_id),
                )
                changed=self.conn.execute("SELECT changes()").fetchone()[0]
                if changed != 1:
                    self.conn.rollback()
                    return None
                self.conn.commit()
                return self.get(job_id)
            except Exception:
                self.conn.rollback()
                raise

    def set_status(self, job_id, status, result=None, error=None):
        now=datetime.now(timezone.utc).isoformat()
        with self._lock:
            self.conn.execute(
                "UPDATE jobs SET status=?, result_json=?, error_json=?, updated_at=? WHERE job_id=?",
                (
                    status,
                    json.dumps(_json_safe(result), ensure_ascii=False) if result is not None else None,
                    json.dumps(_json_safe(error), ensure_ascii=False) if error is not None else None,
                    now,
                    job_id,
                )
            )
            self.conn.commit()

    def get(self, job_id):
        with self._lock:
            row=self.conn.execute(
                "SELECT job_id,project_id,request,status,result_json,error_json,created_at,updated_at,context_json FROM jobs WHERE job_id=?",
                (job_id,)
            ).fetchone()
            if not row:
                return None
            keys=["job_id","project_id","request","status","result_json","error_json","created_at","updated_at","context_json"]
            d=dict(zip(keys,row))
            context=json.loads(d.pop("context_json")) if d.get("context_json") else self._context()
            d["audience"]=context.get("audience")
            d["goal"]=context.get("goal")
            d["constraints"]=context.get("constraints",[])
            d["language"]=context.get("language","en")
            d["result"]=json.loads(d.pop("result_json")) if d["result_json"] else None
            d["error"]=json.loads(d.pop("error_json")) if d["error_json"] else None
            return d

    def list(self, limit=50):
        limit=max(1,min(int(limit),200))
        with self._lock:
            rows=self.conn.execute(
                "SELECT job_id FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self.get(row[0]) for row in rows]

    def close(self):
        with getattr(self, "_lock", threading.RLock()):
            conn=getattr(self, "conn", None)
            if conn is not None:
                conn.close()
                self.conn=None
