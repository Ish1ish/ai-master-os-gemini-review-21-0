import json
import os
import sqlite3
from .events import RunEvent


class SQLiteAuditLog:
    """Durable drop-in audit log with the same interface as AuditLog."""

    def __init__(self, path):
        self.path = str(path)
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS run_events(
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                state TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                component TEXT NOT NULL,
                status TEXT NOT NULL,
                details_json TEXT NOT NULL,
                parent_event_id TEXT
            )
        """)
        self.conn.commit()
        self._closed = False

    def append(self, run_id, event_type, state, component, status, details, parent_event_id=None):
        if self._closed or self.conn is None:
            raise RuntimeError("audit_log_closed")
        from .events import utc_now
        ts = utc_now()
        cur = self.conn.execute(
            "INSERT INTO run_events(run_id,event_type,state,timestamp,component,status,details_json,parent_event_id) VALUES(?,?,?,?,?,?,?,?)",
            (run_id, event_type, state, ts, component, status, json.dumps(details or {}, ensure_ascii=False), parent_event_id),
        )
        self.conn.commit()
        return RunEvent(
            run_id=run_id,
            event_id=f"EV-{cur.lastrowid:06d}",
            event_type=event_type,
            state=state,
            timestamp=ts,
            component=component,
            status=status,
            details=details or {},
            parent_event_id=parent_event_id,
        )

    def _rows(self, where="", params=()):
        rows = self.conn.execute(
            "SELECT event_id,run_id,event_type,state,timestamp,component,status,details_json,parent_event_id FROM run_events " + where + " ORDER BY event_id",
            params,
        ).fetchall()
        return [
            RunEvent(
                run_id=r[1], event_id=f"EV-{r[0]:06d}", event_type=r[2], state=r[3], timestamp=r[4],
                component=r[5], status=r[6], details=json.loads(r[7] or "{}"), parent_event_id=r[8]
            ).to_dict()
            for r in rows
        ]

    def for_run(self, run_id):
        return self._rows("WHERE run_id=?", (run_id,))

    def all(self):
        return self._rows()

    def close(self):
        conn = getattr(self, "conn", None)
        if conn is not None:
            conn.close()
            self.conn = None
        self._closed = True
