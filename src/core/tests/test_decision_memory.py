import os
import tempfile
import unittest

from src.decision_memory import CounterfactualDecisionMemory


def prediction(decision="REVIEW", risk="HIGH"):
    return {
        "status": "REVIEW", "project_id": "P1", "requested_by": "operator",
        "decision": decision, "risk": risk, "plan_hash": "PLAN-1", "side_effects": "NONE",
        "actions": [{"action": "publish_public_content", "predicted_decision": decision, "predicted_risk": risk}],
        "summary": {"estimated_approvals": 1},
    }


class TestCounterfactualDecisionMemory(unittest.TestCase):
    def test_record_is_idempotent_for_same_prediction(self):
        with tempfile.TemporaryDirectory() as td:
            m = CounterfactualDecisionMemory(os.path.join(td, "cf.sqlite3"))
            try:
                a = m.record_prediction(project_id="P1", requested_by="operator", prediction=prediction())
                b = m.record_prediction(project_id="P1", requested_by="operator", prediction=prediction())
                self.assertEqual(a, b)
                self.assertEqual(a["status"], "PREDICTED")
            finally:
                m.close()

    def test_observe_exact_match_is_positive_calibration(self):
        with tempfile.TemporaryDirectory() as td:
            m = CounterfactualDecisionMemory(os.path.join(td, "cf.sqlite3"))
            try:
                p = m.record_prediction(project_id="P1", requested_by="operator", prediction=prediction())
                out = m.observe_outcome(prediction_id=p["prediction_id"], actual={"decision":"REVIEW","risk":"HIGH","execution_status":"COMPLETED"})
                self.assertEqual(out["status"], "OBSERVED")
                self.assertEqual(out["learning"]["calibration"], "EXACT_MATCH")
                self.assertEqual(out["learning"]["score"], 1.0)
            finally:
                m.close()

    def test_underprediction_is_negative_signal(self):
        with tempfile.TemporaryDirectory() as td:
            m = CounterfactualDecisionMemory(os.path.join(td, "cf.sqlite3"))
            try:
                p = m.record_prediction(project_id="P1", requested_by="operator", prediction=prediction("AUTO_ALLOW", "LOW"))
                out = m.observe_outcome(prediction_id=p["prediction_id"], actual={"decision":"BLOCK","risk":"HIGH"})
                self.assertEqual(out["learning"]["calibration"], "UNDERPREDICTED_RISK")
                self.assertLess(out["learning"]["score"], 0)
            finally:
                m.close()

    def test_double_observation_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            m = CounterfactualDecisionMemory(os.path.join(td, "cf.sqlite3"))
            try:
                p = m.record_prediction(project_id="P1", requested_by="operator", prediction=prediction())
                actual = {"decision":"REVIEW","risk":"HIGH"}
                first = m.observe_outcome(prediction_id=p["prediction_id"], actual=actual)
                second = m.observe_outcome(prediction_id=p["prediction_id"], actual={"decision":"BLOCK","risk":"HIGH"})
                self.assertEqual(first, second)
            finally:
                m.close()

    def test_context_separates_pending_from_observed(self):
        with tempfile.TemporaryDirectory() as td:
            m = CounterfactualDecisionMemory(os.path.join(td, "cf.sqlite3"))
            try:
                p1 = m.record_prediction(project_id="P1", requested_by="operator", prediction=prediction())
                m.record_prediction(project_id="P1", requested_by="operator", prediction={**prediction(), "plan_hash":"PLAN-2"})
                m.observe_outcome(prediction_id=p1["prediction_id"], actual={"decision":"REVIEW","risk":"HIGH"})
                ctx = m.calibration_context("P1")
                self.assertEqual(ctx["prediction_count"], 2)
                self.assertEqual(ctx["observed_count"], 1)
                self.assertEqual(ctx["pending_observations"], 1)
            finally:
                m.close()


if __name__ == "__main__":
    unittest.main()
