import unittest

from src.decision_memory import CounterfactualDecisionMemory
from src.adaptive_decision import AdaptiveDecisionIntelligence


class TestContextualAdaptiveDecision(unittest.TestCase):
    def _prediction(self, i, *, action="SEARCH", tool="TAVILY", risk="LOW", tenant="T1"):
        return {
            "decision": "AUTO_ALLOW",
            "risk": risk,
            "plan_hash": f"CTX-{i}",
            "side_effects": "NONE",
            "tenant_id": tenant,
            "actions": [{"action_type": action, "tool": tool}],
            "evidence": [{"source": "LOCAL"}],
        }

    def _record(self, mem, i, actual, **kwargs):
        rec = mem.record_prediction(project_id="P1", requested_by="op", prediction=self._prediction(i, **kwargs))
        mem.observe_outcome(prediction_id=rec["prediction_id"], actual=actual)

    def test_matching_context_raises_caution_without_polluting_other_contexts(self):
        mem = CounterfactualDecisionMemory(":memory:")
        try:
                for i in range(2):
                    self._record(mem, i, {"decision": "REVIEW", "risk": "HIGH"})
                self._record(mem, 9, {"decision": "REVIEW", "risk": "HIGH"}, action="WRITE", tool="LOCAL")
                out = AdaptiveDecisionIntelligence(mem).advise_for_context(
                    "P1", candidate_prediction=self._prediction("candidate", action="SEARCH", tool="TAVILY")
                )
                self.assertEqual(out["scope"], "CONTEXTUAL")
                self.assertEqual(out["contextual_sample_count"], 2)
                self.assertEqual(out["advisory_posture"], "ELEVATED_CAUTION")
        finally:
            mem.close()

    def test_no_context_uses_project_fallback(self):
        mem = CounterfactualDecisionMemory(":memory:")
        try:
                for i in range(3):
                    self._record(mem, i, {"decision": "REVIEW", "risk": "HIGH"})
                out = AdaptiveDecisionIntelligence(mem).advise_for_context(
                    "P1", candidate_prediction=self._prediction("candidate", action="WRITE", tool="LOCAL")
                )
                self.assertEqual(out["scope"], "PROJECT_FALLBACK")
                self.assertEqual(out["contextual_sample_count"], 0)
                self.assertEqual(out["project_sample_count"], 3)
        finally:
            mem.close()

    def test_tenant_partition_changes_context(self):
        mem = CounterfactualDecisionMemory(":memory:")
        try:
                for i in range(2):
                    self._record(mem, i, {"decision": "REVIEW", "risk": "HIGH"}, tenant="T1")
                out = AdaptiveDecisionIntelligence(mem).advise_for_context(
                    "P1", tenant_id="T2", candidate_prediction=self._prediction("candidate", tenant="T2")
                )
                self.assertEqual(out["scope"], "PROJECT_FALLBACK")
                self.assertEqual(out["contextual_sample_count"], 0)
        finally:
            mem.close()

    def test_uncertainty_is_exposed_for_small_context_history(self):
        mem = CounterfactualDecisionMemory(":memory:")
        try:
            self._record(mem, 0, {"decision": "REVIEW", "risk": "HIGH"})
            out = AdaptiveDecisionIntelligence(mem).advise_for_context(
                "P1", candidate_prediction=self._prediction("candidate", action="SEARCH", tool="TAVILY")
            )
            self.assertEqual(out["uncertainty"]["uncertainty_band"], "HIGH")
            self.assertEqual(out["uncertainty"]["reliability_band"], "LOW")
            self.assertIn("calibration_uncertainty_high", out["reasons"])
            self.assertEqual(out["advisory_posture"], "ELEVATED_CAUTION")
        finally:
            mem.close()

    def test_strong_history_can_reduce_advisory_uncertainty_to_low(self):
        mem = CounterfactualDecisionMemory(":memory:")
        try:
            for i in range(12):
                self._record(mem, i, {"decision": "AUTO_ALLOW", "risk": "LOW"})
            out = AdaptiveDecisionIntelligence(mem).advise_for_context(
                "P1", candidate_prediction=self._prediction("candidate", action="SEARCH", tool="TAVILY")
            )
            self.assertEqual(out["uncertainty"]["uncertainty_band"], "LOW")
            self.assertEqual(out["uncertainty"]["reliability_band"], "STRONG")
        finally:
            mem.close()

    def test_governance_authority_is_preserved(self):
        mem = CounterfactualDecisionMemory(":memory:")
        try:
                out = AdaptiveDecisionIntelligence(mem).advise_for_context(
                    "P1",
                    candidate_prediction={
                        "decision": "BLOCK",
                        "risk": "HIGH",
                        "plan_hash": "X",
                        "side_effects": "NONE",
                        "actions": [{"action_type": "SEARCH", "tool": "TAVILY"}],
                    },
                )
                self.assertEqual(out["candidate_decision"], "BLOCK")
                self.assertEqual(out["governance_authority"], "POLICY_AND_GOVERNANCE_REMAIN_AUTHORITATIVE")
        finally:
            mem.close()


if __name__ == "__main__": unittest.main()
