import tempfile
import unittest

from src.advanced_outcome_analysis_runtime import AdvancedOutcomeAnalysisRuntime
from src.advanced_outcome_analysis_store import AdvancedOutcomeAnalysisStore
from src.outcome_intelligence_store import OutcomeIntelligenceStore


class TestAdvancedOutcomeAnalysisRuntime(unittest.TestCase):
    def sample(self, aid: str, signal="POSITIVE_CALIBRATION"):
        return {
            "assessment_id": aid,
            "trace_id": f"TR-{aid}",
            "project_id": "P-RUNTIME",
            "target_status": "MET",
            "outcome_success": True,
            "outcome_quality": "FULL_SUCCESS",
            "decision_quality": "SOUND_DECISION",
            "attribution": "DECISION",
            "learning_signal": signal,
            "evidence_sufficient": True,
        }

    def test_runtime_reads_v15_and_persists_v16(self):
        with tempfile.TemporaryDirectory() as td:
            v15 = OutcomeIntelligenceStore(td + "/v15.sqlite3")
            v16 = AdvancedOutcomeAnalysisStore(td + "/v16.sqlite3")
            for aid in ("1", "2", "3"):
                v15.record(self.sample(aid))
            runtime = AdvancedOutcomeAnalysisRuntime(v15, v16)
            result = runtime.analyze_project("P-RUNTIME")
            self.assertEqual(result["analysis"]["analysis_status"], "ANALYZED")
            self.assertEqual(result["persistence"]["status"], "RECORDED")
            self.assertTrue(result["advisory_only"])
            self.assertTrue(result["governance_unchanged"])
            self.assertFalse(result["external_action_executed"])
            self.assertFalse(result["o43_memory_mutated"])
            v15.close()
            v16.close()

    def test_runtime_replay_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            v15 = OutcomeIntelligenceStore(td + "/v15.sqlite3")
            v16 = AdvancedOutcomeAnalysisStore(td + "/v16.sqlite3")
            for aid in ("1", "2", "3"):
                v15.record(self.sample(aid))
            runtime = AdvancedOutcomeAnalysisRuntime(v15, v16)
            first = runtime.analyze_project("P-RUNTIME")
            second = runtime.analyze_project("P-RUNTIME")
            self.assertEqual(first["analysis"]["analysis_id"], second["analysis"]["analysis_id"])
            self.assertEqual(second["persistence"]["status"], "IDEMPOTENT_REPLAY")
            v15.close()
            v16.close()


if __name__ == "__main__":
    unittest.main()
