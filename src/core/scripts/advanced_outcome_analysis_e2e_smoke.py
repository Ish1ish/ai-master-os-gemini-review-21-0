from __future__ import annotations

import tempfile

from src.advanced_outcome_analysis_runtime import AdvancedOutcomeAnalysisRuntime
from src.advanced_outcome_analysis_store import AdvancedOutcomeAnalysisStore
from src.outcome_intelligence_store import OutcomeIntelligenceStore


def row(aid, signal="POSITIVE_CALIBRATION", quality="FULL_SUCCESS", dq="SOUND_DECISION", attr="DECISION", success=True, target="MET"):
    return {
        "assessment_id": aid,
        "trace_id": f"TRACE-{aid}",
        "project_id": "AOA-E2E",
        "learning_signal": signal,
        "outcome_quality": quality,
        "decision_quality": dq,
        "attribution": attr,
        "outcome_success": success,
        "target_status": target,
        "evidence_sufficient": True,
    }


with tempfile.TemporaryDirectory() as td:
    v15 = OutcomeIntelligenceStore(td + "/v15.sqlite3")
    v16 = AdvancedOutcomeAnalysisStore(td + "/v16.sqlite3")

    v15.record(row("1"))
    v15.record(row("2"))
    v15.record(row("3", signal="REFINE", quality="FAILED", dq="EXECUTION_MISMATCH", attr="EXECUTION", success=False))
    v15.record(row("4"))

    runtime = AdvancedOutcomeAnalysisRuntime(v15, v16)

    first = runtime.analyze_project("AOA-E2E", limit=10, window_size=4, minimum_sample_size=3)
    assert first["analysis"]["analysis_status"] == "ANALYZED"
    assert first["persistence"]["status"] == "RECORDED"
    print("V15_ASSESSMENTS_TO_V16_ANALYSIS PASS")

    second = runtime.analyze_project("AOA-E2E", limit=10, window_size=4, minimum_sample_size=3)
    assert second["analysis"]["analysis_id"] == first["analysis"]["analysis_id"]
    assert second["persistence"]["status"] == "IDEMPOTENT_REPLAY"
    print("V16_ANALYSIS_PERSISTENCE PASS")

    stored = v16.get(first["analysis"]["analysis_id"])
    assert stored == first["analysis"]
    assert first["o43_memory_mutated"] is False
    assert first["external_action_executed"] is False
    print("V16_BOUNDARY_INTEGRITY PASS")
    print({
        "analysis_id": first["analysis"]["analysis_id"],
        "sample_size": first["analysis"]["sample_size"],
        "advisory_route": first["analysis"]["advisory_route"],
        "confidence": first["analysis"]["confidence"],
    })
    print("V16_END_TO_END_IDEMPOTENCY PASS")
    print("ALL V1.6 END-TO-END CHECKS PASSED.")

    v15.close()
    v16.close()
