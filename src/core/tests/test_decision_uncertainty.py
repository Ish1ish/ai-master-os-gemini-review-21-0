import unittest

from src.decision_uncertainty import DecisionUncertainty


class TestDecisionUncertainty(unittest.TestCase):
    def test_sample_sufficiency_bands(self):
        self.assertEqual(DecisionUncertainty.sample_sufficiency(0), "NO_HISTORY")
        self.assertEqual(DecisionUncertainty.sample_sufficiency(2), "MINIMAL")
        self.assertEqual(DecisionUncertainty.sample_sufficiency(4), "LIMITED")
        self.assertEqual(DecisionUncertainty.sample_sufficiency(7), "MODERATE")
        self.assertEqual(DecisionUncertainty.sample_sufficiency(10), "STRONG")

    def test_stability_is_unknown_without_two_scores(self):
        self.assertEqual(DecisionUncertainty.stability_band([]), "UNKNOWN")
        self.assertEqual(DecisionUncertainty.stability_band([1]), "UNKNOWN")

    def test_volatile_scores_raise_uncertainty(self):
        self.assertEqual(DecisionUncertainty.stability_band([-1, 1, -1, 1]), "VOLATILE")
        self.assertEqual(
            DecisionUncertainty.uncertainty_band(sample_count=4, drift="STABLE", stability="VOLATILE"),
            "HIGH",
        )

    def test_small_history_is_high_uncertainty(self):
        self.assertEqual(
            DecisionUncertainty.uncertainty_band(sample_count=2, drift="STABLE", stability="UNKNOWN"),
            "HIGH",
        )

    def test_deterioration_is_high_uncertainty(self):
        self.assertEqual(
            DecisionUncertainty.uncertainty_band(sample_count=20, drift="DETERIORATING", stability="STABLE"),
            "HIGH",
        )

    def test_large_stable_history_can_be_strongly_reliable(self):
        out = DecisionUncertainty.assess(
            accuracy=0.9,
            sample_count=12,
            recent_scores=[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            drift="STABLE",
        )
        self.assertEqual(out["sample_sufficiency"], "STRONG")
        self.assertEqual(out["uncertainty_band"], "LOW")
        self.assertEqual(out["reliability_band"], "STRONG")
        self.assertEqual(out["calibration_stability"], "STABLE")

    def test_accuracy_does_not_override_weak_sample_size(self):
        out = DecisionUncertainty.assess(
            accuracy=1.0,
            sample_count=2,
            recent_scores=[1, 1],
            drift="STABLE",
        )
        self.assertEqual(out["uncertainty_band"], "HIGH")
        self.assertEqual(out["reliability_band"], "LOW")

    def test_reliability_is_not_probability(self):
        out = DecisionUncertainty.assess(
            accuracy=0.8,
            sample_count=5,
            recent_scores=[1, 1, 1, -1, 1],
            drift="STABLE",
        )
        self.assertIn(out["reliability_band"], {"LOW", "MODERATE"})
        self.assertIn("probability", out["boundary"].lower())

    def test_no_history_is_unknown_not_low(self):
        out = DecisionUncertainty.assess(
            accuracy=None,
            sample_count=0,
            recent_scores=[],
            drift="UNKNOWN",
        )
        self.assertEqual(out["uncertainty_band"], "UNKNOWN")
        self.assertEqual(out["reliability_band"], "NONE")
        self.assertEqual(out["sample_sufficiency"], "NO_HISTORY")

    def test_reason_flags_are_deterministic(self):
        out = DecisionUncertainty.assess(
            accuracy=0.5,
            sample_count=2,
            recent_scores=[-1, 1],
            drift="DETERIORATING",
        )
        self.assertEqual(
            out["reasons"],
            ["insufficient_calibration_history", "calibration_deteriorating", "calibration_volatile", "low_calibration_reliability"],
        )


if __name__ == "__main__":
    unittest.main()
