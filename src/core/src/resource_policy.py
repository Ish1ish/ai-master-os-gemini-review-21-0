from typing import Dict, Any


RESOURCE_RULES = {
    "run": {
        "read": "run:read",
        "cancel": "run:cancel",
        "retry": "run:retry",
    },
    "approval": {
        "read": "approval:read",
        "decide": "approval:decide",
    },
    "queue": {
        "recover": "queue:recover",
    },
    "dead_letter": {
        "replay": "dlq:replay",
    },
    "control": {
        "read": "control:read",
    },
}


class ResourceAuthorizer:
    def required_scope(self, resource: str, action: str):
        return RESOURCE_RULES.get(resource, {}).get(action)

    def authorize(self, rbac, principal, resource, action, owner_id=None):
        scope = self.required_scope(resource, action)
        if not scope:
            return {"status": "DENY", "reason": "unknown_resource_action"}
        # Simple tenant/resource boundary: a viewer/operator may inspect their permitted
        # resources; sensitive decision authority is represented by role scope.
        result = rbac.authorize(principal, scope)
        if result["status"] != "ALLOW":
            return result
        if resource == "approval" and action == "decide" and "approver" not in principal.get("roles", []) and "admin" not in principal.get("roles", []):
            return {"status": "DENY", "reason": "approval_authority_required"}
        return {"status": "ALLOW", "required_scope": scope}
