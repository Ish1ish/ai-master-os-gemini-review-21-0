from typing import Dict, Any, Set


DEFAULT_SCOPES = {
    "read_knowledge",
    "read_web",
    "generate_content",
    "write_memory",
    "read_memory",
    "audit_write",
    "request_approval",
}


class PolicyEngine:
    """
    Central permission policy. Unknown actions default to deny.
    """

    CONSEQUENT_ACTIONS = {
        "publish_public_content",
        "send_external_message",
        "spend_ad_budget",
        "change_price",
        "payment_or_refund",
        "delete_or_modify_critical_data",
        "activate_integration",
    }

    def __init__(self, allowed_scopes: Set[str] | None = None):
        self.allowed_scopes = set(allowed_scopes or DEFAULT_SCOPES)

    def authorize(self, action: str, required_scope: str, external_effect=False) -> Dict[str, Any]:
        if required_scope not in self.allowed_scopes:
            return {
                "status": "DENY",
                "reason": "scope_not_allowed",
                "action": action,
                "required_scope": required_scope,
            }

        if external_effect or action in self.CONSEQUENT_ACTIONS:
            return {
                "status": "REQUIRE_APPROVAL",
                "reason": "consequential_action",
                "action": action,
                "required_scope": required_scope,
            }

        return {
            "status": "ALLOW",
            "action": action,
            "required_scope": required_scope,
        }
