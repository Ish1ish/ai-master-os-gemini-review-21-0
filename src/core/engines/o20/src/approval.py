from typing import Dict, Any, List


CONSEQUENTIAL_ACTIONS = {
    "send_external_message",
    "publish_public_content",
    "spend_ad_budget",
    "change_price",
    "payment_or_refund",
    "delete_or_modify_critical_data",
    "activate_integration",
}


class AutomationApprovalGate:
    def build(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        gates = []

        for step in steps:
            action = step.get("action_key", "")
            explicit = bool(step.get("requires_approval", False))
            required = explicit or action in CONSEQUENTIAL_ACTIONS

            if required:
                gates.append({
                    "step_id": step.get("step_id"),
                    "action_key": action,
                    "required": True,
                    "gate_type": "HUMAN_APPROVAL",
                })

        return {
            "gates": gates,
            "approval_required": bool(gates),
        }
