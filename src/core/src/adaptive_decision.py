from __future__ import annotations

from typing import Any, Dict

from .decision_fingerprint import DecisionFingerprint
from .decision_uncertainty import DecisionUncertainty


class AdaptiveDecisionIntelligence:
    """Deterministic advisory layer over contextual calibration memory.

    Memory can influence advisory posture only. Governance policy remains authoritative.
    v0.6 adds contextual fingerprints while retaining the v0.5 project-level fallback.
    """

    POSTURE_RANK = {"NORMAL": 0, "ELEVATED_CAUTION": 1, "HIGH_CAUTION": 2}

    def __init__(self, memory):
        self.memory = memory

    @staticmethod
    def _profile(rows):
        observed = [r for r in rows if r.get("status") == "OBSERVED" and r.get("learning")]
        exact = [r for r in observed if r["learning"].get("calibration") == "EXACT_MATCH"]
        under = [r for r in observed if r["learning"].get("calibration") == "UNDERPREDICTED_RISK"]
        over = [r for r in observed if r["learning"].get("calibration") == "OVERPREDICTED_RISK"]
        total = len(observed)
        accuracy = round(len(exact) / total, 3) if total else None
        avg = round(sum(float(r["learning"].get("score", 0.0)) for r in observed) / total, 3) if total else None
        return {
            "sample_count": total,
            "exact_match": len(exact),
            "underpredicted_risk": len(under),
            "overpredicted_risk": len(over),
            "accuracy": accuracy,
            "average_learning_score": avg,
        }

    @classmethod
    def _advise_from_profile(cls, profile, candidate_decision, candidate_risk, *, reasons_prefix=""):
        candidate_decision = str(candidate_decision or "BLOCK").upper()
        candidate_risk = str(candidate_risk or "HIGH").upper()
        reasons = []
        posture = "NORMAL"
        if profile["sample_count"] >= 2 and profile["underpredicted_risk"] >= 1:
            posture = "ELEVATED_CAUTION"
            reasons.append(f"{reasons_prefix}contextual_risk_underprediction" if reasons_prefix else "repeated_risk_underprediction")
        if profile["sample_count"] >= 4 and profile["underpredicted_risk"] / max(profile["sample_count"], 1) >= 0.5:
            posture = "HIGH_CAUTION"
            reasons.append(f"{reasons_prefix}high_contextual_underprediction_rate" if reasons_prefix else "high_underprediction_rate")
        if candidate_risk == "HIGH" and profile["underpredicted_risk"] >= 1 and posture == "NORMAL":
            posture = "ELEVATED_CAUTION"
            reasons.append(f"{reasons_prefix}high_risk_with_prior_underprediction" if reasons_prefix else "high_risk_with_prior_underprediction")
        return posture, reasons

    @classmethod
    def advise(cls, *, memory_context: Dict[str, Any], candidate_decision: str, candidate_risk: str) -> Dict[str, Any]:
        candidate_decision = str(candidate_decision or "BLOCK").upper()
        candidate_risk = str(candidate_risk or "HIGH").upper()
        rows = memory_context.get("records") or []
        profile = cls._profile(rows)
        reasons = []
        posture = "NORMAL"

        if profile["sample_count"] >= 3 and profile["underpredicted_risk"] >= 2:
            posture = "ELEVATED_CAUTION"
            reasons.append("repeated_risk_underprediction")
        if profile["sample_count"] >= 5 and profile["underpredicted_risk"] / max(profile["sample_count"], 1) >= 0.5:
            posture = "HIGH_CAUTION"
            reasons.append("high_underprediction_rate")
        if candidate_risk == "HIGH" and profile["underpredicted_risk"] >= 1 and posture == "NORMAL":
            posture = "ELEVATED_CAUTION"
            reasons.append("high_risk_with_prior_underprediction")

        return {
            "status": "READY" if profile["sample_count"] else "COLD_START",
            "candidate_decision": candidate_decision,
            "candidate_risk": candidate_risk,
            "advisory_posture": posture,
            "reasons": reasons,
            "profile": profile,
            "governance_authority": "POLICY_AND_GOVERNANCE_REMAIN_AUTHORITATIVE",
            "boundary": "Calibration memory may increase caution but cannot lower or bypass a governance decision.",
        }

    def advise_for_project(self, project_id: str, *, candidate_decision: str, candidate_risk: str, limit: int = 50) -> Dict[str, Any]:
        context = self.memory.calibration_context(project_id, limit=limit)
        return self.advise(memory_context=context, candidate_decision=candidate_decision, candidate_risk=candidate_risk)

    def advise_for_context(
        self,
        project_id: str,
        *,
        candidate_prediction: Dict[str, Any],
        tenant_id: str | None = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Apply caution to the closest historical decision context.

        A candidate is compared against prior observed records using stable context
        dimensions. Project-wide calibration is retained as a deterministic fallback
        when there are no matching contextual observations.
        """
        context = self.memory.calibration_context(project_id, limit=limit)
        rows = context.get("records") or []
        candidate_fp = DecisionFingerprint.build(
            prediction=candidate_prediction,
            project_id=project_id,
            tenant_id=tenant_id,
        )
        contextual = []
        for row in rows:
            if row.get("status") != "OBSERVED" or not row.get("learning"):
                continue
            prior_fp = DecisionFingerprint.from_record(row)
            if DecisionFingerprint.matches(candidate_fp, prior_fp):
                contextual.append(row)

        if contextual:
            profile = self._profile(contextual)
            posture, reasons = self._advise_from_profile(
                profile,
                candidate_fp["decision"],
                candidate_fp["risk_class"],
                reasons_prefix="contextual_",
            )
            scope = "CONTEXTUAL"
        else:
            profile = self._profile(rows)
            posture, reasons = self._advise_from_profile(
                profile,
                candidate_fp["decision"],
                candidate_fp["risk_class"],
                reasons_prefix="project_fallback_",
            )
            scope = "PROJECT_FALLBACK" if profile["sample_count"] else "COLD_START"

        observed_scores = [
            float((r.get("learning") or {}).get("score", 0.0))
            for r in contextual
            if r.get("learning")
        ]
        exact = [r for r in contextual if (r.get("learning") or {}).get("calibration") == "EXACT_MATCH"]
        accuracy = round(len(exact) / len(contextual), 3) if contextual else None
        candidate_fp["historical_accuracy"] = DecisionFingerprint.accuracy_band(accuracy, len(contextual))
        candidate_fp["calibration_drift"] = DecisionFingerprint.drift_band(observed_scores)
        uncertainty = DecisionUncertainty.assess(
            accuracy=accuracy,
            sample_count=len(contextual),
            recent_scores=observed_scores,
            drift=candidate_fp["calibration_drift"],
        )

        if uncertainty["uncertainty_band"] == "HIGH" and posture == "NORMAL" and contextual:
            posture = "ELEVATED_CAUTION"
            reasons.append("calibration_uncertainty_high")
        if candidate_fp["calibration_drift"] == "DETERIORATING" and posture == "NORMAL" and contextual:
            posture = "ELEVATED_CAUTION"
            reasons.append("contextual_calibration_deteriorating")
        for reason in uncertainty["reasons"]:
            if reason not in reasons:
                reasons.append(reason)

        return {
            "status": "READY" if contextual or rows else "COLD_START",
            "scope": scope,
            "candidate_decision": candidate_fp["decision"],
            "candidate_risk": candidate_fp["risk_class"],
            "advisory_posture": posture,
            "reasons": reasons,
            "candidate_fingerprint": candidate_fp,
            "profile": profile,
            "uncertainty": uncertainty,
            "contextual_sample_count": len(contextual),
            "project_sample_count": len(rows),
            "governance_authority": "POLICY_AND_GOVERNANCE_REMAIN_AUTHORITATIVE",
            "boundary": "Contextual calibration may increase caution but cannot lower, bypass, or override a governance decision.",
        }
