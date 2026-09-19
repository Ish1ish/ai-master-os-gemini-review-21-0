from typing import Dict, Any, List


class WorkflowToolPlanner:
    def build(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        mappings = []

        for step in steps:
            step_type = step.get("type")
            if step_type == "action":
                tool_class = "registered_action_tool"
            elif step_type == "transform":
                tool_class = "data_transform"
            elif step_type == "condition":
                tool_class = "condition_engine"
            else:
                tool_class = "manual_review"

            mappings.append({
                "step_id": step.get("step_id"),
                "tool_class": tool_class,
                "requires_approval": bool(step.get("requires_approval", False)),
            })

        return {"tool_mappings": mappings}
