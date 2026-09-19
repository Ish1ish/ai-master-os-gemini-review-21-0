import sqlite3
import threading


class TenantQuota:
    """Durable, per-tenant quota accounting with atomic reservation."""

    def __init__(self, max_active_jobs=5, path=None):
        if max_active_jobs < 1:
            raise ValueError("max_active_jobs must be >= 1")
        self.max_active_jobs = max_active_jobs
        self.path = path or ":memory:"
        self.conn = sqlite3.connect(self.path, check_same_thread=False, timeout=30)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS tenant_quota "
            "(tenant_id TEXT PRIMARY KEY, active INTEGER NOT NULL DEFAULT 0)"
        )
        self.conn.commit()
        self._lock = threading.RLock()
        self._closed = False

    def _ensure_open(self):
        if self._closed:
            raise RuntimeError("tenant_quota_closed")

    def reserve(self, tenant_id):
        self._ensure_open()
        if not tenant_id:
            return {"status": "DENY", "reason": "tenant_required"}
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            row = self.conn.execute(
                "SELECT active FROM tenant_quota WHERE tenant_id=?", (tenant_id,)
            ).fetchone()
            current = row[0] if row else 0
            if current >= self.max_active_jobs:
                self.conn.rollback()
                return {
                    "status": "QUOTA_EXCEEDED",
                    "tenant_id": tenant_id,
                    "limit": self.max_active_jobs,
                    "active": current,
                }
            next_active = current + 1
            self.conn.execute(
                "INSERT INTO tenant_quota(tenant_id,active) VALUES(?,?) "
                "ON CONFLICT(tenant_id) DO UPDATE SET active=excluded.active",
                (tenant_id, next_active),
            )
            self.conn.commit()
            return {"status": "RESERVED", "tenant_id": tenant_id, "active": next_active}

    def release(self, tenant_id):
        self._ensure_open()
        if not tenant_id:
            return {"status": "DENY", "reason": "tenant_required"}
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            row = self.conn.execute(
                "SELECT active FROM tenant_quota WHERE tenant_id=?", (tenant_id,)
            ).fetchone()
            current = row[0] if row else 0
            next_active = max(0, current - 1)
            self.conn.execute(
                "INSERT INTO tenant_quota(tenant_id,active) VALUES(?,?) "
                "ON CONFLICT(tenant_id) DO UPDATE SET active=excluded.active",
                (tenant_id, next_active),
            )
            self.conn.commit()
            return {"status": "RELEASED", "tenant_id": tenant_id, "active": next_active}

    def active(self, tenant_id):
        self._ensure_open()
        row = self.conn.execute(
            "SELECT active FROM tenant_quota WHERE tenant_id=?", (tenant_id,)
        ).fetchone()
        return row[0] if row else 0

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
