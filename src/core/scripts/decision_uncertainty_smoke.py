from __future__ import annotations

from src.adaptive_decision import AdaptiveDecisionIntelligence
from src.decision_memory import CounterfactualDecisionMemory


def main() -> None:
    memory = CounterfactualDecisionMemory(":memory:")
    try:
        prior = {
            "decision": "AUTO_ALLOW",
            "risk": "LOW",
            "plan_hash": "V07-SMOKE-1",
            "side_effects": "NONE",
            "tenant_id": "T1",
            "actions": [{"action_type": "SEARCH", "tool": "TAVILY"}],
            "evidence": [{"source": "TAVILY"}],
        }
        for i in range(2):
            candidate = dict(prior)
            candidate["plan_hash"] = f"V07-SMOKE-{i}"
            record = memory.record_prediction(project_id="P1", requested_by="operator", prediction=candidate)
            memory.observe_outcome(
                prediction_id=record["prediction_id"],
                actual={"decision": "REVIEW", "risk": "HIGH"},
            )

        result = AdaptiveDecisionIntelligence(memory).advise_for_context(
            "P1", candidate_prediction=prior, tenant_id="T1"
        )
        assert result["scope"] == "CONTEXTUAL"
        assert result["contextual_sample_count"] == 2
        assert result["uncertainty"]["uncertainty_band"] == "HIGH"
        assert result["uncertainty"]["reliability_band"] == "LOW"
        assert result["governance_authority"] == "POLICY_AND_GOVERNANCE_REMAIN_AUTHORITATIVE"
        print("V0.7 DECISION UNCERTAINTY SMOKE PASS")
        print({
            "scope": result["scope"],
            "posture": result["advisory_posture"],
            "samples": result["contextual_sample_count"],
            "uncertainty": result["uncertainty"]["uncertainty_band"],
            "reliability": result["uncertainty"]["reliability_band"],
            "stability": result["uncertainty"]["calibration_stability"],
            "governance_authority": result["governance_authority"],
        })
    finally:
        memory.close()


if __name__ == "__main__":
    main()
