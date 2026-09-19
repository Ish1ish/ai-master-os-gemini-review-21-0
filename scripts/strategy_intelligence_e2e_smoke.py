from src.strategy_intelligence_runtime import StrategyIntelligenceRuntime
from src.strategy_intelligence_store import StrategyIntelligenceStore


def main():
    store = StrategyIntelligenceStore(":memory:")
    runtime = StrategyIntelligenceRuntime(store)

    ctx = {
        "context_id": "ADC-E2E",
        "project_id": "SI-E2E",
        "advisory_posture": "NORMAL",
        "advisory_decision": "RECOMMEND",
    }
    candidates = [
        {"strategy_id": "A", "prior_success_rate": .85, "sample_size": 9, "execution_mismatch_rate": .05, "evidence_strength": .9, "context_match": .9},
        {"strategy_id": "B", "prior_success_rate": .55, "sample_size": 7, "execution_mismatch_rate": .0, "evidence_strength": .7, "context_match": .6},
    ]

    first = runtime.rank("SI-E2E", decision_context=ctx, candidates=candidates)
    assert first["analysis"]["top_strategy_id"] == "A"
    print("V17_CONTEXT_TO_V18_STRATEGY PASS")

    replay = runtime.rank("SI-E2E", decision_context=ctx, candidates=candidates)
    assert replay["persistence"]["status"] == "IDEMPOTENT_REPLAY"
    print("V18_STRATEGY_IDEMPOTENCY PASS")

    assert replay["governance_unchanged"] is True
    assert replay["external_action_executed"] is False
    assert replay["o43_memory_mutated"] is False
    print("V18_BOUNDARY_INTEGRITY PASS")
    print({"analysis_id": replay["analysis"]["analysis_id"], "top_strategy_id": replay["analysis"]["top_strategy_id"]})
    print("ALL V1.8 END-TO-END CHECKS PASSED.")
    store.close()


if __name__ == "__main__":
    main()
