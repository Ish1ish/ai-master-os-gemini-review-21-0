import unittest

from src.advanced_outcome_analysis import AdvancedOutcomeAnalysis


def assessment(
    aid: str,
    signal: str = "POSITIVE_CALIBRATION",
    quality: str = "FULL_SUCCESS",
    decision_quality: str = "SOUND_DECISION",
    attribution: str = "DECISION",
    success: bool = True,
    target: str = "MET",
    evidence: bool = True,
):
    return {
        "assessment_id": aid,
        "project_id": "P-AOA",
        "learning_signal": signal,
        "outcome_quality": quality,
        "decision_quality": decision_quality,
        "attribution": attribution,
        "outcome_success": success,
        "target_status": target,
        "evidence_sufficient": evidence,
    }


class TestAdvancedOutcomeAnalysis(unittest.TestCase):
    def setUp(self):
        self.analyzer = AdvancedOutcomeAnalysis()

    def test_repeated_decision_misses_are_detected(self):
        rows = [
            assessment("1", signal="NEGATIVE_SIGNAL", quality="MISSED_TARGET", decision_quality="TARGET_MISSED", success=True, target="MISSED"),
            assessment("2", signal="NEGATIVE_SIGNAL", quality="MISSED_TARGET", decision_quality="TARGET_MISSED", success=True, target="MISSED"),
            assessment("3", signal="POSITIVE_CALIBRATION"),
            assessment("4", signal="NEGATIVE_SIGNAL", quality="MISSED_TARGET", decision_quality="TARGET_MISSED", success=True, target="MISSED"),
        ]
        out = self.analyzer.analyze(project_id="P-AOA", assessments=rows)
        self.assertEqual(out["analysis_status"], "ANALYZED")
        self.assertIn("REPEATED_DECISION_MISSES", out["findings"])
        self.assertEqual(out["advisory_route"], "REFINE_DECISION")

    def test_execution_mismatch_routes_to_investigation(self):
        rows = [
            assessment("1", signal="REFINE", quality="FAILED", decision_quality="EXECUTION_MISMATCH", attribution="EXECUTION", success=False),
            assessment("2", signal="REFINE", quality="FAILED", decision_quality="EXECUTION_MISMATCH", attribution="EXECUTION", success=False),
            assessment("3", signal="POSITIVE_CALIBRATION"),
        ]
        out = self.analyzer.analyze(project_id="P-AOA", assessments=rows)
        self.assertIn("REPEATED_EXECUTION_MISMATCH", out["findings"])
        self.assertEqual(out["advisory_route"], "INVESTIGATE_EXECUTION")

    def test_weak_evidence_blocks_strong_route(self):
        rows = [
            assessment("1", evidence=False),
            assessment("2", evidence=False),
            assessment("3", evidence=True),
        ]
        out = self.analyzer.analyze(project_id="P-AOA", assessments=rows)
        self.assertIn("EVIDENCE_COVERAGE_WEAK", out["findings"])
        self.assertEqual(out["advisory_route"], "COLLECT_MORE_EVIDENCE")

    def test_small_sample_is_inconclusive(self):
        rows = [assessment("1"), assessment("2")]
        out = self.analyzer.analyze(project_id="P-AOA", assessments=rows)
        self.assertEqual(out["analysis_status"], "INSUFFICIENT_SAMPLE")
        self.assertEqual(out["confidence"], "unknown")
        self.assertEqual(out["advisory_route"], "COLLECT_MORE_EVIDENCE")

    def test_unknown_targets_surface_pattern(self):
        rows = [
            assessment("1", target="UNKNOWN", signal="DO_NOT_LEARN", evidence=False),
            assessment("2", target="UNKNOWN", signal="DO_NOT_LEARN", evidence=False),
            assessment("3", target="MET"),
        ]
        out = self.analyzer.analyze(project_id="P-AOA", assessments=rows)
        self.assertIn("TARGET_UNKNOWN_PATTERN", out["findings"])

    def test_analysis_id_is_deterministic(self):
        rows = [assessment("1"), assessment("2"), assessment("3")]
        a = self.analyzer.analyze(project_id="P-AOA", assessments=rows)
        b = self.analyzer.analyze(project_id="P-AOA", assessments=rows)
        self.assertEqual(a["analysis_id"], b["analysis_id"])

    def test_project_mismatch_is_rejected(self):
        row = assessment("1")
        row["project_id"] = "OTHER"
        with self.assertRaises(ValueError):
            self.analyzer.analyze(project_id="P-AOA", assessments=[row])

    def test_governance_boundary_is_explicit(self):
        rows = [assessment("1"), assessment("2"), assessment("3")]
        out = self.analyzer.analyze(project_id="P-AOA", assessments=rows)
        self.assertIn("does not prove future outcomes", out["boundary"])


if __name__ == "__main__":
    unittest.main()
