from typing import Dict, Any, List


class WorkflowBuilder:
    def build(self, process: Dict[str, Any]) -> Dict[str, Any]:
        name = process.get("name", "Untitled Workflow")
        purpose = process.get("purpose", "")
        trigger = process.get("trigger", "manual")

        steps = process.get("steps") or [
            {
                "step_id": "STEP-01",
                "name": "Validate Input",
                "type": "condition",
                "action": "Check required inputs before execution.",
            },
            {
                "step_id": "STEP-02",
                "name": "Prepare Data",
                "type": "transform",
                "action": "Normalize and structure the data needed by downstream actions.",
            },
            {
                "step_id": "STEP-03",
                "name": "Execute Core Action",
                "type": "action",
                "action": "Perform the main workflow operation.",
            },
            {
                "step_id": "STEP-04",
                "name": "Validate Result",
                "type": "condition",
                "action": "Check the output against the expected result contract.",
            },
        ]

        return {
            "workflow_id": f"WF-{name.upper().replace(' ', '-')[:24]}",
            "name": name,
            "purpose": purpose,
            "trigger": trigger,
            "steps": steps,
            "version": "v1.0",
            "status": "DRAFT",
        }
