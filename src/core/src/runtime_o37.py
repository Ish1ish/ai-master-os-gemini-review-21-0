from .resource_service import MultiTenantService


class O37Runtime:
    def __init__(self, root):
        self.tenants = MultiTenantService(root)
        self._closed = False

    def provision_demo(self):
        for tenant_id, name in (("TENANT-A", "Tenant A"), ("TENANT-B", "Tenant B")):
            if not self.tenants.store.get_tenant(tenant_id):
                self.tenants.create_tenant(tenant_id, name)
        projects = (
            ("P-A", "TENANT-A", "user-a", "Project A"),
            ("P-B", "TENANT-B", "user-b", "Project B"),
            ("P-A2", "TENANT-A", "operator-a", "Project A2"),
        )
        for project_id, tenant_id, owner_id, name in projects:
            if not self.tenants.store.get_project(project_id):
                self.tenants.create_project(project_id, tenant_id, owner_id, name)

    def principal(self, principal_id, tenant_id, roles, scopes=None):
        return {
            "principal_id": principal_id,
            "tenant_id": tenant_id,
            "roles": roles,
            "scopes": scopes or [],
            "active": True,
        }

    def close(self):
        if self._closed:
            return
        self.tenants.close()
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
