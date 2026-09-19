import os
import sqlite3
from datetime import datetime, timezone


class TenantStore:
    def __init__(self, path):
        self.path = path
        self._closed = False
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False, timeout=30)
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS tenants(
                tenant_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS projects(
                project_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                owner_principal_id TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id)
            )"""
        )
        self.conn.commit()

    def _ensure_open(self):
        if self._closed:
            raise RuntimeError("tenant_store_closed")

    def create_tenant(self, tenant_id, name):
        self._ensure_open()
        self.conn.execute(
            "INSERT INTO tenants VALUES(?,?,?,?)",
            (tenant_id, name, "ACTIVE", datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()

    def create_project(self, project_id, tenant_id, owner_principal_id, name):
        self._ensure_open()
        if not self.get_tenant(tenant_id):
            return {"status": "TENANT_NOT_FOUND"}
        self.conn.execute(
            "INSERT INTO projects VALUES(?,?,?,?,?,?)",
            (
                project_id,
                tenant_id,
                owner_principal_id,
                name,
                "ACTIVE",
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self.conn.commit()
        return {"status": "CREATED", "project_id": project_id}

    def get_tenant(self, tenant_id):
        self._ensure_open()
        row = self.conn.execute(
            "SELECT tenant_id,name,status,created_at FROM tenants WHERE tenant_id=?",
            (tenant_id,),
        ).fetchone()
        return None if not row else {
            "tenant_id": row[0], "name": row[1], "status": row[2], "created_at": row[3]
        }

    def get_project(self, project_id):
        self._ensure_open()
        row = self.conn.execute(
            "SELECT project_id,tenant_id,owner_principal_id,name,status,created_at "
            "FROM projects WHERE project_id=?",
            (project_id,),
        ).fetchone()
        return None if not row else {
            "project_id": row[0],
            "tenant_id": row[1],
            "owner_principal_id": row[2],
            "name": row[3],
            "status": row[4],
            "created_at": row[5],
        }

    def close(self):
        if self._closed:
            return
        try:
            self.conn.close()
        finally:
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
