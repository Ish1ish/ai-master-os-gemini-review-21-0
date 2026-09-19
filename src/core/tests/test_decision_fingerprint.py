import unittest

from src.decision_fingerprint import DecisionFingerprint


class TestDecisionFingerprint(unittest.TestCase):
    def _prediction(self, **extra):
        base = {
            "decision": "AUTO_ALLOW",
            "risk": "LOW",
            "actions": [
                {"action_type": "SEARCH", "tool": "TAVILY"},
                {"action_type": "SUMMARIZE", "tool": "LOCAL"},
            ],
            "evidence": [{"source": "TAVILY"}, {"source": "LOCAL"}],
        }
        base.update(extra)
        return base

    def test_fingerprint_is_deterministic(self):
        a = DecisionFingerprint.build(prediction=self._prediction(), project_id="P1", tenant_id="T1")
        b = DecisionFingerprint.build(prediction=self._prediction(), project_id="P1", tenant_id="T1")
        self.assertEqual(a["fingerprint"], b["fingerprint"])
        self.assertEqual(a["match_key"], b["match_key"])

    def test_action_and_tool_dimensions_are_normalized(self):
        out = DecisionFingerprint.build(
            prediction=self._prediction(actions=[{"type": "search", "tool_name": "tavily"}]),
            project_id="P1",
        )
        self.assertEqual(out["action_types"], ["SEARCH"])
        self.assertEqual(out["tools"], ["TAVILY"])

    def test_evidence_pattern_classifies_mixed(self):
        out = DecisionFingerprint.build(prediction=self._prediction(), project_id="P1")
        self.assertEqual(out["evidence_pattern"], "MIXED_EVIDENCE")

    def test_accuracy_band_and_drift_are_bounded(self):
        self.assertEqual(DecisionFingerprint.accuracy_band(0.9, 10), "HIGH")
        self.assertEqual(DecisionFingerprint.accuracy_band(0.6, 10), "MEDIUM")
        self.assertEqual(DecisionFingerprint.accuracy_band(0.2, 10), "LOW")
        self.assertEqual(DecisionFingerprint.accuracy_band(1.0, 0), "UNKNOWN")
        self.assertEqual(DecisionFingerprint.drift_band([1, -1]), "DETERIORATING")
        self.assertEqual(DecisionFingerprint.drift_band([-1, 1]), "IMPROVING")
        self.assertEqual(DecisionFingerprint.drift_band([1, 1]), "STABLE")

    def test_learned_dimensions_do_not_change_matching_key(self):
        a = DecisionFingerprint.build(prediction=self._prediction(), project_id="P1", historical_accuracy=0.9, sample_count=10)
        b = DecisionFingerprint.build(prediction=self._prediction(), project_id="P1", historical_accuracy=0.1, sample_count=10)
        self.assertEqual(a["fingerprint"], b["fingerprint"])
        self.assertNotEqual(a["historical_accuracy"], b["historical_accuracy"])

    def test_project_and_tenant_are_context_dimensions(self):
        a = DecisionFingerprint.build(prediction=self._prediction(), project_id="P1", tenant_id="T1")
        b = DecisionFingerprint.build(prediction=self._prediction(), project_id="P2", tenant_id="T1")
        c = DecisionFingerprint.build(prediction=self._prediction(), project_id="P1", tenant_id="T2")
        self.assertNotEqual(a["fingerprint"], b["fingerprint"])
        self.assertNotEqual(a["fingerprint"], c["fingerprint"])

    def test_none_action_and_evidence_have_explicit_categories(self):
        out = DecisionFingerprint.build(
            prediction={"decision": "BLOCK", "risk": "HIGH", "actions": []},
            project_id="P1",
        )
        self.assertEqual(out["action_types"], ["NONE"])
        self.assertEqual(out["tools"], ["NONE"])
        self.assertEqual(out["evidence_pattern"], "NO_EVIDENCE")
        self.assertEqual(out["historical_accuracy"], "UNKNOWN")
        self.assertEqual(out["calibration_drift"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
