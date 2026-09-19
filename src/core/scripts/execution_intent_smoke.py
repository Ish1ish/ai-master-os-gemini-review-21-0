from src.execution_intent_planner import ExecutionIntentPlanner

plan = {
    "status": "RECOMMEND",
    "project_id": "phase2-demo",
    "plan_id": "UDI-DEMO-001",
    "selected_route": {
        "provider": "provider_a",
        "tool": "search_a",
        "score": 1.05,
        "source_score": 0.88,
        "cost_usd": 0.01,
        "latency_ms": 110.0,
    },
    "decision_basis": {
        "uncertainty": "LOW",
        "reliability": "STRONG",
        "resource_pressure": "NORMAL",
        "latency_posture": "NORMAL",
        "cost_posture": "WITHIN_BUDGET",
    },
    "governance_required": True,
}

intent = ExecutionIntentPlanner.build_intent(
    decision_plan=plan,
    action="publish_public_content",
    payload={"content": "bounded test"},
    project_id="phase2-demo",
    run_id="R-UDI-001",
    requested_by="operator",
    context={"environment": "offline"},
)
assert intent["status"] == "PLANNED"
preflight = ExecutionIntentPlanner.preflight(intent, expected_project_id="phase2-demo")
assert preflight["status"] == "READY_FOR_GOVERNED_SUBMISSION"
assert preflight["governance_review_required"] is True
assert preflight["external_action_executed"] is False
assert intent["execution_started"] is False
assert intent["execution_completed"] is False
print("PHASE 2 EXECUTION PLANNING SMOKE PASS")
print(intent)
print("PHASE 2 EXECUTION PLANNING CONTRACT PASS")
print("PHASE 2 EXECUTION PLANNING SAFETY BOUNDARY PASS")
print("ALL PHASE 2 EXECUTION PLANNING CHECKS PASSED.")
