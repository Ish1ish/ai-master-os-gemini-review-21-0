from __future__ import annotations

from typing import Any, Dict, Optional


SIGNAL_TO_DECISION = {
    "POSITIVE_CALIBRATION": "GO",
    "REFINE": "REFINE",
    "NEGATIVE_SIGNAL": "NO-GO",
}


def to_o43_lesson(assessment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convert a verified v1.5 assessment into an O43-shaped lesson.

    This is an adapter only. It does not write to O43 memory and never creates
    a learning-driving lesson from DO_NOT_LEARN.
    """
    signal = str(assessment.get("learning_signal") or "").upper()
    if signal == "DO_NOT_LEARN":
        return None

    refs = list(assessment.get("evidence_refs") or [])
    if not refs or not assessment.get("evidence_sufficient"):
        return None

    decision = SIGNAL_TO_DECISION.get(signal)
    if decision is None:
        raise ValueError("unsupported_learning_signal")

    quality = assessment.get("outcome_quality") or "INCONCLUSIVE"
    attribution = assessment.get("attribution") or "INSUFFICIENT_EVIDENCE"
    summary = (
        f"Observed outcome quality={quality}; "
        f"decision quality={assessment.get('decision_quality')}; "
        f"attribution={attribution}."
    )

    return {
        "lesson_id": "OIL-LESSON-" + str(assessment["assessment_id"]).replace("OIA-", ""),
        "experiment_id": assessment.get("trace_id"),
        "decision": decision,
        "confidence": assessment.get("confidence") or "medium",
        "summary": summary,
        "learning": (
            f"Learning signal {signal} was derived from observed outcome evidence; "
            "it is bounded to this observed run."
        ),
        "evidence_refs": refs,
        "sample_size": 1,
        "metrics": {
            "outcome_success": bool(assessment.get("outcome_success")),
        },
        "next_step": (
            "Proceed with the smallest bounded next test."
            if signal == "POSITIVE_CALIBRATION"
            else "Refine one material variable before the next test."
            if signal == "REFINE"
            else "Route to a new hypothesis; do not repeat unchanged."
        ),
        "re_run_context": {
            "trace_id": assessment.get("trace_id"),
            "assessment_id": assessment.get("assessment_id"),
            "attribution": attribution,
        },
        "scope": {
            "project_id": assessment.get("project_id"),
            "source": "OUTCOME_INTELLIGENCE_v1.5",
        },
        "provenance": {
            "assessment_id": assessment.get("assessment_id"),
            "trace_id": assessment.get("trace_id"),
        },
    }
