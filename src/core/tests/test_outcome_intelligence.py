import unittest

from src.outcome_intelligence import OutcomeIntelligence


class TestOutcomeIntelligence(unittest.TestCase):
    def setUp(self):
        self.engine = OutcomeIntelligence()
        self.trace = {
            "trace_id": "TRC-TEST",
            "project_id": "P1",
            "decision_plan_id": "D1",
            "intent_id": "I1",
            "execution_id": "E1",
            "decision_status": "RECOMMEND",
            "execution_state": "SUCCEEDED",
            "outcome_status": "SUCCEEDED",
            "outcomes": [{"success": True}],
        }

    def test_full_success_produces_positive_calibration(self):
        out = self.engine.assess(
            trace=self.trace,
            target_status="MET",
            evidence_refs=["EVID-1"],
            confidence="high",
        )
        self.assertEqual(out["outcome_quality"], "FULL_SUCCESS")
        self.assertEqual(out["decision_quality"], "SOUND_DECISION")
        self.assertEqual(out["attribution"], "DECISION")
        self.assertEqual(out["learning_signal"], "POSITIVE_CALIBRATION")
        self.assertTrue(out["learning_driving"])

    def test_partial_success_produces_refine(self):
        out = self.engine.assess(
            trace=self.trace,
            target_status="PARTIAL",
            evidence_refs=["EVID-1"],
            confidence="high",
        )
        self.assertEqual(out["outcome_quality"], "PARTIAL_SUCCESS")
        self.assertEqual(out["decision_quality"], "TARGET_MISSED")
        self.assertEqual(out["learning_signal"], "REFINE")

    def test_missed_target_produces_negative_signal(self):
        out = self.engine.assess(
            trace=self.trace,
            target_status="MISSED",
            evidence_refs=["EVID-1"],
            confidence="high",
        )
        self.assertEqual(out["outcome_quality"], "MISSED_TARGET")
        self.assertEqual(out["decision_quality"], "TARGET_MISSED")
        self.assertEqual(out["learning_signal"], "NEGATIVE_SIGNAL")

    def test_unknown_target_does_not_drive_learning(self):
        out = self.engine.assess(
            trace=self.trace,
            target_status="UNKNOWN",
            evidence_refs=["EVID-1"],
            confidence="high",
        )
        self.assertEqual(out["outcome_quality"], "INCONCLUSIVE")
        self.assertEqual(out["decision_quality"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(out["attribution"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(out["learning_signal"], "DO_NOT_LEARN")
        self.assertFalse(out["learning_driving"])

    def test_missing_evidence_does_not_drive_learning(self):
        out = self.engine.assess(
            trace=self.trace,
            target_status="MET",
            evidence_refs=[],
            confidence="high",
        )
        self.assertFalse(out["evidence_sufficient"])
        self.assertEqual(out["decision_quality"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(out["learning_signal"], "DO_NOT_LEARN")

    def test_execution_failure_is_attributed_to_execution(self):
        trace = dict(self.trace)
        trace["execution_state"] = "FAILED"
        trace["outcome_status"] = "FAILED"
        trace["outcomes"] = [{"success": False}]
        out = self.engine.assess(
            trace=trace,
            target_status="MET",
            evidence_refs=["EVID-1"],
            confidence="high",
        )
        self.assertEqual(out["outcome_quality"], "FAILED")
        self.assertEqual(out["attribution"], "EXECUTION")
        self.assertEqual(out["decision_quality"], "EXECUTION_MISMATCH")
        self.assertEqual(out["learning_signal"], "REFINE")

    def test_assessment_id_is_deterministic(self):
        args = {
            "trace": self.trace,
            "target_status": "MET",
            "evidence_refs": ["EVID-1"],
            "confidence": "high",
        }
        a = self.engine.assess(**args)
        b = self.engine.assess(**args)
        self.assertEqual(a["assessment_id"], b["assessment_id"])

    def test_invalid_values_fail_closed(self):
        with self.assertRaises(ValueError):
            self.engine.assess(
                trace=self.trace,
                target_status="NOT_A_STATUS",
            )
        with self.assertRaises(ValueError):
            self.engine.assess(
                trace=self.trace,
                target_status="MET",
                confidence="certain",
            )
        with self.assertRaises(ValueError):
            self.engine.assess(
                trace=self.trace,
                target_status="MET",
                attribution_hint="NOT_VALID",
            )


if __name__ == "__main__":
    unittest.main()
