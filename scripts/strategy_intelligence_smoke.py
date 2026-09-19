from src.strategy_intelligence import StrategyIntelligence


def main():
    engine = StrategyIntelligence()
    ctx = {
        "context_id": "ADC-DEMO",
        "project_id": "STRATEGY-DEMO",
        "advisory_posture": "NORMAL",
        "advisory_decision": "RECOMMEND",
    }
    candidates = [
        {"strategy_id": "A", "prior_success_rate": .8, "sample_size": 8, "execution_mismatch_rate": .1, "evidence_strength": .8, "context_match": .9},
        {"strategy_id": "B", "prior_success_rate": .6, "sample_size": 7, "execution_mismatch_rate": .0, "evidence_strength": .9, "context_match": .6},
    ]
    r = engine.rank(project_id="STRATEGY-DEMO", decision_context=ctx, candidates=candidates)
    assert r["route"] == "RANKED_ADVISORY"
    assert r["top_strategy_id"] == "A"
    assert r["external_action_executed"] is False
    assert r["o43_memory_mutated"] is False

    print("STRATEGY INTELLIGENCE SMOKE PASS")
    print({"analysis_id": r["analysis_id"], "top_strategy_id": r["top_strategy_id"], "route": r["route"], "confidence": r["confidence"]})
    print("STRATEGY_RANKING PASS")
    print("ADVISORY_BOUNDARY PASS")
    print("ALL STRATEGY INTELLIGENCE CHECKS PASSED.")


if __name__ == "__main__":
    main()
