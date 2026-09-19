import sqlite3
import os
import json
from datetime import datetime, timezone


class OperatorStore:
    """
    Durable operator/control-plane records.
    """

    def __init__(self, path):
        self.path=path
        os.makedirs(os.path.dirname(os.path.abspath(path)),exist_ok=True)
        self.conn=sqlite3.connect(path,check_same_thread=False)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS operator_actions(
                action_id INTEGER PRIMARY KEY AUTOINCREMENT,
                operator_id TEXT NOT NULL,
                action TEXT NOT NULL,
                target_id TEXT NOT NULL,
                payload TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def record(self, operator_id, action, target_id, payload=None, status="RECORDED"):
        self.conn.execute(
            "INSERT INTO operator_actions(operator_id,action,target_id,payload,status,created_at) VALUES(?,?,?,?,?,?)",
            (operator_id,action,target_id,json.dumps(payload or {}),status,datetime.now(timezone.utc).isoformat())
        )
        self.conn.commit()

    def list_actions(self, target_id=None):
        if target_id:
            rows=self.conn.execute(
                "SELECT operator_id,action,target_id,payload,status,created_at FROM operator_actions WHERE target_id=? ORDER BY action_id",
                (target_id,)
            ).fetchall()
        else:
            rows=self.conn.execute(
                "SELECT operator_id,action,target_id,payload,status,created_at FROM operator_actions ORDER BY action_id"
            ).fetchall()
        return [
            {"operator_id":a,"action":b,"target_id":c,"payload":json.loads(d or "{}"),"status":e,"created_at":f}
            for a,b,c,d,e,f in rows
        ]

    def close(self):
        conn=getattr(self, "conn", None)
        if conn is not None:
            conn.close()
            self.conn=None
