from src.adaptive_decision_context_store import AdaptiveDecisionContextStore
from src.adaptive_decision_runtime import AdaptiveDecisionRuntime


def main():
    analysis = {
        "analysis_id": "AOA-E2E-001",
        "project_id": "ADAPT-E2E",
        "analysis_status": "ANALYZED",
        "advisory_route": "REFINE_DECISION",
        "findings": ["REPEATED_DECISION_MISSES"],
        "sample_size": 6,
        "confidence": "medium",
    }

    store = AdaptiveDecisionContextStore(":memory:")
    runtime = AdaptiveDecisionRuntime(store)

    first = runtime.build_context(
        "ADAPT-E2E",
        analysis=analysis,
        candidate_decision="RECOMMEND",
    )
    assert first["context"]["advisory_decision"] == "REFINE"
    print("V16_ANALYSIS_TO_V17_CONTEXT PASS")

    assert first["persistence"]["status"] == "RECORDED"
    print("V17_CONTEXT_PERSISTENCE PASS")

    replay = runtime.build_context(
        "ADAPT-E2E",
        analysis=analysis,
        candidate_decision="RECOMMEND",
    )
    assert replay["persistence"]["status"] == "IDEMPOTENT_REPLAY"
    print("V17_CONTEXT_IDEMPOTENCY PASS")

    assert replay["governance_unchanged"] is True
    assert replay["external_action_executed"] is False
    assert replay["o43_memory_mutated"] is False
    print("V17_BOUNDARY_INTEGRITY PASS")

    print({
        "context_id": replay["context"]["context_id"],
        "advisory_decision": replay["context"]["advisory_decision"],
        "advisory_posture": replay["context"]["advisory_posture"],
    })
    print("ALL V1.7 END-TO-END CHECKS PASSED.")
    store.close()


if __name__ == "__main__":
    main()
