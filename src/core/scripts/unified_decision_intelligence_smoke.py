from src.unified_decision_intelligence import UnifiedDecisionIntelligence

out = UnifiedDecisionIntelligence.plan(
    project_id="phase2-demo",
    context={"tenant": "default", "action_type": "INTERNAL_ANALYSIS"},
    candidates=[
        {"provider": "provider_a", "tool": "search_a", "score": 0.82, "cost_usd": 0.01, "latency_ms": 120},
        {"provider": "provider_b", "tool": "search_b", "score": 0.79, "cost_usd": 0.015, "latency_ms": 90},
    ],
    uncertainty="LOW",
    reliability="STRONG",
    resource_pressure="ELEVATED",
    latency_posture="NORMAL",
    cost_posture="WITHIN_BUDGET",
)
assert out["status"] in {"RECOMMEND", "REFINE"}
assert out["selected_route"] is not None
assert out["external_action_executed"] is False
assert out["governance_authority"] == "POLICY_AND_GOVERNANCE_REMAIN_AUTHORITATIVE"
print("PHASE 2 UNIFIED DECISION INTELLIGENCE SMOKE PASS")
print(out)
