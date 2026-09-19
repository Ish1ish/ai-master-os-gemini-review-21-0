from src.outcome_intelligence import OutcomeIntelligence


def main():
    engine = OutcomeIntelligence()

    trace = {
        "trace_id": "TRC-OIL-DEMO",
        "project_id": "OIL-DEMO",
        "decision_plan_id": "UDI-OIL-001",
        "intent_id": "EINT-OIL-001",
        "execution_id": "EXE-OIL-001",
        "decision_status": "RECOMMEND",
        "execution_state": "SUCCEEDED",
        "outcome_status": "SUCCEEDED",
        "outcomes": [{"success": True}],
    }

    result = engine.assess(
        trace=trace,
        target_status="MET",
        evidence_refs=["EVID-OIL-1", "EVID-OIL-2"],
        confidence="high",
    )

    assert result["outcome_quality"] == "FULL_SUCCESS"
    assert result["decision_quality"] == "SOUND_DECISION"
    assert result["attribution"] == "DECISION"
    assert result["learning_signal"] == "POSITIVE_CALIBRATION"
    assert result["learning_driving"] is True
    assert result["schema_version"] == "OIL-v1.0"

    print("OUTCOME INTELLIGENCE SMOKE PASS")
    print(result)
    print("OUTCOME_TO_LEARNING_SIGNAL PASS")
    print("ALL OUTCOME INTELLIGENCE CHECKS PASSED.")


if __name__ == "__main__":
    main()
