from src.adaptive_decision_context import AdaptiveDecisionContext


def main():
    adapter = AdaptiveDecisionContext()
    analysis = {
        "analysis_id": "AOA-ADAPT-001",
        "project_id": "ADAPT-DEMO",
        "analysis_status": "ANALYZED",
        "advisory_route": "REFINE_DECISION",
        "findings": ["REPEATED_DECISION_MISSES"],
        "sample_size": 6,
        "confidence": "medium",
    }
    result = adapter.build(
        project_id="ADAPT-DEMO",
        analysis=analysis,
        candidate_decision="RECOMMEND",
    )

    assert result["status"] == "ADVISORY_READY"
    assert result["advisory_posture"] == "ELEVATED_CAUTION"
    assert result["advisory_decision"] == "REFINE"
    assert result["governance_required"] is True
    assert result["external_action_executed"] is False
    assert result["o43_memory_mutated"] is False

    print("ADAPTIVE DECISION CONTEXT SMOKE PASS")
    print({
        "context_id": result["context_id"],
        "status": result["status"],
        "candidate_decision": result["candidate_decision"],
        "advisory_decision": result["advisory_decision"],
        "advisory_posture": result["advisory_posture"],
    })
    print("LEARNING_TO_CONTEXT PASS")
    print("GOVERNANCE_BOUNDARY PASS")
    print("ALL ADAPTIVE DECISION CONTEXT CHECKS PASSED.")


if __name__ == "__main__":
    main()
