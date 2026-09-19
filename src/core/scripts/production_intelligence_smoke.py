from src.production_intelligence import ProductionIntelligence
from src.production_intelligence_store import ProductionIntelligenceStore


def main() -> None:
    obs = {
        "provider": "provider-A",
        "tool": "search",
        "observed_at": "2026-09-12T00:00:00Z",
        "cost_usd": 0.02,
        "latency_ms": 120,
        "success_rate": 0.995,
        "sample_count": 100,
        "cpu_pct": 88,
        "memory_pct": 60,
        "freshness": "FRESH",
        "evidence_refs": ["OPS-SMOKE"],
    }
    normalized = ProductionIntelligence.normalize_observation(obs)
    assert normalized["status"] == "NORMALIZED"
    assessment = ProductionIntelligence.assess([obs], max_latency_ms=300, max_cost_usd=0.10)
    recommendation = ProductionIntelligence.recommend(
        project_id="V09-SMOKE",
        context={"risk_class": "LOW"},
        assessment=assessment,
        candidates=[
            {"provider": "provider-A", "tool": "search", "cost_usd": 0.02, "latency_ms": 120, "success_rate": 0.995},
            {"provider": "provider-B", "tool": "search", "cost_usd": 0.03, "latency_ms": 150, "success_rate": 0.99},
        ],
    )
    assert recommendation["status"] == "ADVISORY"
    assert recommendation["external_action_executed"] is False
    assert recommendation["requires_governance"] is True
    assert recommendation["caution"] == "ELEVATED"
    store = ProductionIntelligenceStore(":memory:")
    try:
        store.create("OPS-SMOKE-1", "V09-SMOKE", normalized)
        assert store.get("OPS-SMOKE-1")["payload"]["status"] == "NORMALIZED"
    finally:
        store.close()
    print("V0.9 PRODUCTION INTELLIGENCE SMOKE PASS")
    print({
        "assessment": assessment["status"],
        "latency_posture": assessment["latency_posture"],
        "cost_posture": assessment["cost_posture"],
        "resource_pressure": assessment["resource_pressure"]["band"],
        "recommendation": recommendation["action"],
        "caution": recommendation["caution"],
        "external_action_executed": recommendation["external_action_executed"],
        "governance_authority": recommendation["governance_authority"],
    })


if __name__ == "__main__":
    main()
