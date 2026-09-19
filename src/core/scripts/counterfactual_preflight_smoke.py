from src.counterfactual_preflight import CounterfactualPreflight


class DemoGovernance:
    def classify(self, action, context):
        if action in {"generate_internal_draft", "read_only_inspection"}:
            return {
                "decision": "AUTO_ALLOW",
                "risk": "LOW",
                "reason_code": "low_risk_high_confidence",
                "approval_required": False,
                "execution_allowed": True,
            }
        return {
            "decision": "REVIEW",
            "risk": "HIGH",
            "reason_code": "high_risk_action",
            "approval_required": True,
            "execution_allowed": False,
        }


class DemoRegistry:
    def resolve(self, tool_name):
        return object()


if __name__ == "__main__":
    engine = CounterfactualPreflight(DemoGovernance(), registry=DemoRegistry())
    plan = [
        {
            "action": "generate_internal_draft",
            "tool_name": "draft_tool",
            "payload": {},
            "idempotency_key": "demo-1",
        },
        {
            "action": "publish_public_content",
            "tool_name": "publisher",
            "payload": {},
            "idempotency_key": "demo-2",
        },
    ]
    print(engine.simulate(project_id="DEMO", requested_by="operator", actions=plan))
