from typing import Dict, Any


VALID_TRIGGERS = {
    "manual",
    "schedule",
    "new_data",
    "threshold",
    "webhook",
    "event",
}


class TriggerPlanner:
    def validate(self, trigger_spec: Dict[str, Any]) -> Dict[str, Any]:
        trigger = trigger_spec.get("type", "manual")
        issues = []

        if trigger not in VALID_TRIGGERS:
            issues.append({
                "type": "unsupported_trigger",
                "trigger": trigger,
            })

        if trigger == "schedule" and not trigger_spec.get("schedule"):
            issues.append({"type": "missing_schedule"})

        if trigger == "threshold" and not trigger_spec.get("condition"):
            issues.append({"type": "missing_threshold_condition"})

        if trigger == "webhook" and not trigger_spec.get("endpoint"):
            issues.append({"type": "missing_webhook_endpoint"})

        return {
            "status": "PASS" if not issues else "FAIL",
            "issues": issues,
            "trigger": trigger,
        }
