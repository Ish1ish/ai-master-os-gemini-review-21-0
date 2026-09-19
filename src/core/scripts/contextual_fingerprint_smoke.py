from __future__ import annotations

from src.adaptive_decision import AdaptiveDecisionIntelligence
from src.decision_memory import CounterfactualDecisionMemory
from src.decision_fingerprint import DecisionFingerprint


def main() -> None:
    memory = CounterfactualDecisionMemory(":memory:")
    try:
        prior = {
            "decision": "AUTO_ALLOW",
            "risk": "LOW",
            "plan_hash": "V06-SMOKE-1",
            "side_effects": "NONE",
            "tenant_id": "T1",
            "actions": [{"action_type": "SEARCH", "tool": "TAVILY"}],
            "evidence": [{"source": "TAVILY"}],
        }
        record = memory.record_prediction(project_id="P1", requested_by="operator", prediction=prior)
        memory.observe_outcome(
            prediction_id=record["prediction_id"],
            actual={"decision": "REVIEW", "risk": "HIGH"},
        )

        candidate = dict(prior)
        candidate["plan_hash"] = "V06-SMOKE-CANDIDATE"
        fingerprint = DecisionFingerprint.build(prediction=candidate, project_id="P1", tenant_id="T1")
        result = AdaptiveDecisionIntelligence(memory).advise_for_context(
            "P1", candidate_prediction=candidate, tenant_id="T1"
        )

        assert result["scope"] == "CONTEXTUAL"
        assert result["contextual_sample_count"] == 1
        assert result["candidate_fingerprint"]["fingerprint"] == fingerprint["fingerprint"]
        assert result["governance_authority"] == "POLICY_AND_GOVERNANCE_REMAIN_AUTHORITATIVE"
        print("V0.6 CONTEXTUAL FINGERPRINT SMOKE PASS")
        print({
            "scope": result["scope"],
            "posture": result["advisory_posture"],
            "contextual_samples": result["contextual_sample_count"],
            "fingerprint": result["candidate_fingerprint"]["fingerprint"],
            "historical_accuracy": result["candidate_fingerprint"]["historical_accuracy"],
            "calibration_drift": result["candidate_fingerprint"]["calibration_drift"],
            "governance_authority": result["governance_authority"],
        })
    finally:
        memory.close()


if __name__ == "__main__":
    main()
