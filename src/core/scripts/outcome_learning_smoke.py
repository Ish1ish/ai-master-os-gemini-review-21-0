import os
import tempfile

from src.outcome_intelligence import OutcomeIntelligence
from src.outcome_intelligence_store import OutcomeIntelligenceStore
from src.learning_signal_adapter import to_o43_lesson


def main():
    with tempfile.TemporaryDirectory() as td:
        engine = OutcomeIntelligence()
        store = OutcomeIntelligenceStore(
            os.path.join(td, "outcome_intelligence.sqlite3")
        )

        trace = {
            "trace_id": "TRC-OIL-LEARN",
            "project_id": "P-OIL",
            "decision_plan_id": "D-OIL",
            "intent_id": "I-OIL",
            "execution_id": "E-OIL",
            "decision_status": "RECOMMEND",
            "execution_state": "SUCCEEDED",
            "outcome_status": "SUCCEEDED",
            "outcomes": [{"success": True}],
        }

        assessment = engine.assess(
            trace=trace,
            target_status="MET",
            evidence_refs=["EVID-1", "EVID-2"],
            confidence="high",
        )
        first = store.record(assessment)
        replay = store.record(assessment)
        lesson = to_o43_lesson(assessment)

        assert first["status"] == "RECORDED"
        assert replay["status"] == "IDEMPOTENT_REPLAY"
        assert lesson is not None
        assert lesson["decision"] == "GO"
        assert lesson["provenance"]["assessment_id"] == assessment["assessment_id"]

        print("OUTCOME INTELLIGENCE PERSISTENCE PASS")
        print("IDEMPOTENT_ASSESSMENT_REPLAY PASS")
        print("O43_LEARNING_HANDOFF PASS")
        print({
            "assessment_id": assessment["assessment_id"],
            "learning_signal": assessment["learning_signal"],
            "o43_decision": lesson["decision"],
            "trace_id": lesson["provenance"]["trace_id"],
        })
        print("ALL OUTCOME LEARNING CHECKS PASSED.")

        store.close()


if __name__ == "__main__":
    main()
