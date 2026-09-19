from __future__ import annotations

from statistics import pstdev
from typing import Any, Iterable, Dict, List


class DecisionUncertainty:
    """Evidence-weighted reliability assessment for historical calibration.

    This layer describes how much the observed calibration history deserves to be
    trusted. It never changes governance decisions and never claims probability.
    """

    @staticmethod
    def sample_sufficiency(sample_count: int) -> str:
        n = max(0, int(sample_count))
        if n == 0:
            return "NO_HISTORY"
        if n <= 2:
            return "MINIMAL"
        if n <= 4:
            return "LIMITED"
        if n <= 9:
            return "MODERATE"
        return "STRONG"

    @staticmethod
    def stability_band(scores: Iterable[float]) -> str:
        values = [float(v) for v in scores]
        if len(values) < 2:
            return "UNKNOWN"
        deviation = pstdev(values)
        if deviation >= 0.75:
            return "VOLATILE"
        return "STABLE"

    @staticmethod
    def uncertainty_band(*, sample_count: int, drift: str, stability: str) -> str:
        n = max(0, int(sample_count))
        drift = str(drift or "UNKNOWN").upper()
        stability = str(stability or "UNKNOWN").upper()
        if n == 0:
            return "UNKNOWN"
        if n <= 2 or drift == "DETERIORATING" or stability == "VOLATILE":
            return "HIGH"
        if n <= 4 or drift == "UNKNOWN":
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def reliability_band(*, sample_count: int, accuracy: Any, uncertainty: str, drift: str, stability: str) -> str:
        n = max(0, int(sample_count))
        if n == 0:
            return "NONE"
        acc = None if accuracy is None else float(accuracy)
        if n >= 10 and acc is not None and acc >= 0.8 and uncertainty == "LOW" and drift != "DETERIORATING" and stability == "STABLE":
            return "STRONG"
        if n >= 5 and acc is not None and acc >= 0.6 and uncertainty in {"LOW", "MEDIUM"} and stability != "VOLATILE":
            return "MODERATE"
        return "LOW"

    @classmethod
    def assess(cls, *, accuracy: Any, sample_count: int, recent_scores: Iterable[float], drift: str) -> Dict[str, Any]:
        scores: List[float] = [float(v) for v in recent_scores]
        sufficiency = cls.sample_sufficiency(sample_count)
        stability = cls.stability_band(scores)
        uncertainty = cls.uncertainty_band(sample_count=sample_count, drift=drift, stability=stability)
        reliability = cls.reliability_band(
            sample_count=sample_count,
            accuracy=accuracy,
            uncertainty=uncertainty,
            drift=drift,
            stability=stability,
        )
        reasons: List[str] = []
        if sample_count <= 2 and sample_count > 0:
            reasons.append("insufficient_calibration_history")
        if drift == "DETERIORATING":
            reasons.append("calibration_deteriorating")
        if stability == "VOLATILE":
            reasons.append("calibration_volatile")
        if reliability == "LOW":
            reasons.append("low_calibration_reliability")
        return {
            "sample_count": int(sample_count),
            "accuracy": None if accuracy is None else round(float(accuracy), 3),
            "sample_sufficiency": sufficiency,
            "calibration_drift": drift,
            "calibration_stability": stability,
            "uncertainty_band": uncertainty,
            "reliability_band": reliability,
            "reasons": reasons,
            "boundary": "Calibration reliability describes evidence strength; it is not a probability and cannot weaken governance.",
        }
