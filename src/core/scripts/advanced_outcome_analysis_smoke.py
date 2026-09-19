from __future__ import annotations

import tempfile

from src.advanced_outcome_analysis import AdvancedOutcomeAnalysis


def row(aid, signal="POSITIVE_CALIBRATION", quality="FULL_SUCCESS", dq="SOUND_DECISION", attr="DECISION", success=True, target="MET"):
    return {
        "assessment_id": aid,
        "project_id": "AOA-SMOKE",
        "learning_signal": signal,
        "outcome_quality": quality,
        "decision_quality": dq,
        "attribution": attr,
        "outcome_success": success,
        "target_status": target,
        "evidence_sufficient": True,
    }


rows = [
    row("A1"),
    row("A2"),
    row("A3", signal="REFINE", quality="FAILED", dq="EXECUTION_MISMATCH", attr="EXECUTION", success=False),
    row("A4", signal="POSITIVE_CALIBRATION"),
]

result = AdvancedOutcomeAnalysis().analyze(
    project_id="AOA-SMOKE",
    assessments=rows,
    window_size=4,
    minimum_sample_size=3,
)

assert result["analysis_status"] == "ANALYZED"
assert result["sample_size"] == 4
assert result["eligible_learning_sample"] == 4
assert "REPEATED_EXECUTION_MISMATCH" not in result["findings"]
assert result["advisory_route"] in {"MAINTAIN", "MONITOR"}

print("ADVANCED OUTCOME ANALYSIS SMOKE PASS")
print({
    "analysis_id": result["analysis_id"],
    "sample_size": result["sample_size"],
    "evidence_sufficiency_rate": result["evidence_sufficiency_rate"],
    "trend": result["trend"],
    "findings": result["findings"],
    "advisory_route": result["advisory_route"],
    "confidence": result["confidence"],
})
print("OBSERVED_PATTERN_ANALYSIS PASS")
print("ADVISORY_BOUNDARY PASS")
print("ALL ADVANCED OUTCOME ANALYSIS CHECKS PASSED.")
