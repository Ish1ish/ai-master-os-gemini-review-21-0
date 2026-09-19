class TenantAuthorizer:
    def can_access_project(self, principal, project):
        if not principal or not principal.get("active"):
            return {"status": "DENY", "reason": "unauthenticated"}
        if not project:
            return {"status": "NOT_FOUND"}

        roles = set(principal.get("roles", []))
        scopes = set(principal.get("scopes", []))
        if "admin" in roles and "tenant:cross" in scopes:
            return {"status": "ALLOW", "reason": "global_admin"}

        if principal.get("tenant_id") != project.get("tenant_id"):
            return {"status": "DENY", "reason": "cross_tenant_access"}

        if project.get("owner_principal_id") == principal.get("principal_id"):
            return {"status": "ALLOW"}
        if roles.intersection({"operator", "approver"}):
            return {"status": "ALLOW"}
        return {"status": "DENY", "reason": "project_ownership_required"}
