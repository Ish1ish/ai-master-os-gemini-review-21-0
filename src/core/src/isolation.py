class IsolationGuard:
    """Fail-closed tenant/project boundary enforcement."""

    def validate(self, principal, tenant_id, project):
        if not principal or not principal.get("active"):
            return {"status": "DENY", "reason": "unauthenticated"}

        principal_tenant = principal.get("tenant_id")
        roles = set(principal.get("roles", []))
        scopes = set(principal.get("scopes", []))

        # A global administrator must carry an explicit cross-tenant authority.
        # Possessing the admin role alone is not enough to bypass tenant isolation.
        global_admin = "admin" in roles and "tenant:cross" in scopes

        if not tenant_id or principal_tenant != tenant_id:
            if global_admin:
                return {"status": "ALLOW", "reason": "global_admin"}
            return {"status": "DENY", "reason": "cross_tenant_access"}

        if project is not None and project.get("tenant_id") != tenant_id:
            if global_admin:
                return {"status": "ALLOW", "reason": "global_admin"}
            return {"status": "DENY", "reason": "cross_tenant_access"}

        return {"status": "ALLOW"}
