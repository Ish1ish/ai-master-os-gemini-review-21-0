from typing import Dict, Any, List


class RecoveryPlanner:
    def build(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        policies = []

        for step in steps:
            policies.append({
                "step_id": step.get("step_id"),
                "on_error": "retry_once_then_escalate",
                "on_timeout": "stop_and_escalate",
                "on_invalid_result": "do_not_continue",
                "idempotency_required": step.get("type") == "action",
            })

        return {"recovery_policies": policies}
