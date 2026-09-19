import os
import tempfile
import unittest

from src.decision_memory import CounterfactualDecisionMemory
from src.adaptive_decision import AdaptiveDecisionIntelligence


class TestAdaptiveDecisionIntelligence(unittest.TestCase):
    def _memory(self, td):
        return CounterfactualDecisionMemory(os.path.join(td, "cf.sqlite3"))

    def _record(self, mem, i, calibration):
        pred={"decision":"AUTO_ALLOW","risk":"LOW","plan_hash":f"P{i}","side_effects":"NONE","actions":[]}
        rec=mem.record_prediction(project_id="P1", requested_by="op", prediction=pred)
        if calibration=="UNDERPREDICTED_RISK":
            mem.observe_outcome(prediction_id=rec["prediction_id"], actual={"decision":"REVIEW","risk":"HIGH"})
        elif calibration=="EXACT_MATCH":
            mem.observe_outcome(prediction_id=rec["prediction_id"], actual={"decision":"AUTO_ALLOW","risk":"LOW"})
        else:
            mem.observe_outcome(prediction_id=rec["prediction_id"], actual={"decision":"AUTO_ALLOW","risk":"LOW"})

    def test_cold_start_is_normal(self):
        with tempfile.TemporaryDirectory() as td:
            mem=self._memory(td)
            try:
                out=AdaptiveDecisionIntelligence(mem).advise_for_project("P1", candidate_decision="REVIEW", candidate_risk="HIGH")
                self.assertEqual(out["status"], "COLD_START")
                self.assertEqual(out["advisory_posture"], "NORMAL")
            finally: mem.close()

    def test_repeated_underprediction_raises_caution(self):
        with tempfile.TemporaryDirectory() as td:
            mem=self._memory(td)
            try:
                for i in range(3): self._record(mem,i,"UNDERPREDICTED_RISK")
                out=AdaptiveDecisionIntelligence(mem).advise_for_project("P1", candidate_decision="REVIEW", candidate_risk="HIGH")
                self.assertEqual(out["advisory_posture"], "ELEVATED_CAUTION")
                self.assertIn("repeated_risk_underprediction", out["reasons"])
            finally: mem.close()

    def test_high_underprediction_rate_raises_high_caution(self):
        with tempfile.TemporaryDirectory() as td:
            mem=self._memory(td)
            try:
                for i in range(6): self._record(mem,i,"UNDERPREDICTED_RISK")
                out=AdaptiveDecisionIntelligence(mem).advise_for_project("P1", candidate_decision="AUTO_ALLOW", candidate_risk="LOW")
                self.assertEqual(out["advisory_posture"], "HIGH_CAUTION")
            finally: mem.close()

    def test_memory_never_downgrades_governance(self):
        out=AdaptiveDecisionIntelligence.advise(memory_context={"records":[]}, candidate_decision="BLOCK", candidate_risk="HIGH")
        self.assertEqual(out["candidate_decision"], "BLOCK")
        self.assertEqual(out["governance_authority"], "POLICY_AND_GOVERNANCE_REMAIN_AUTHORITATIVE")

if __name__ == "__main__": unittest.main()
