import os

from .tenant_store import TenantStore
from .tenant_authz import TenantAuthorizer
from .isolation import IsolationGuard
from .quota import TenantQuota


class MultiTenantService:
    def __init__(self, root, max_active_jobs=5):
        self.root = root
        os.makedirs(root, exist_ok=True)
        self.store = TenantStore(os.path.join(root, "tenancy.sqlite3"))
        self.quota = TenantQuota(max_active_jobs, path=os.path.join(root, "quota.sqlite3"))
        self.authz = TenantAuthorizer()
        self.isolation = IsolationGuard()
        self._closed = False

    def create_tenant(self, tenant_id, name):
        self.store.create_tenant(tenant_id, name)
        return self.store.get_tenant(tenant_id)

    def create_project(self, project_id, tenant_id, owner_principal_id, name):
        return self.store.create_project(project_id, tenant_id, owner_principal_id, name)

    def project(self, principal, project_id):
        if not project_id:
            return {"status": "NOT_FOUND"}
        p = self.store.get_project(project_id)
        if p is None:
            return {"status": "NOT_FOUND"}
        tenant_id = principal.get("tenant_id") if principal else None
        guard = self.isolation.validate(principal, tenant_id, p)
        if guard["status"] != "ALLOW":
            # Never expose the target project's existence across a tenant boundary.
            return guard
        authz = self.authz.can_access_project(principal, p)
        if authz["status"] != "ALLOW":
            return authz
        return {"status": "ALLOW", "project": p}

    def reserve_job(self, principal, project_id):
        access = self.project(principal, project_id)
        if access["status"] != "ALLOW":
            return access
        return self.quota.reserve(principal["tenant_id"])

    def release_job(self, tenant_id):
        return self.quota.release(tenant_id)

    def close(self):
        if self._closed:
            return
        try:
            self.quota.close()
        finally:
            self.store.close()
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
