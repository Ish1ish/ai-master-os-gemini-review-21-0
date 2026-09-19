import os
import tempfile

from src.execution_intent_planner import ExecutionIntentPlanner
from src.execution_observability import ExecutionObservability
from src.execution_observability import ExecutionObservabilityStore
from src.governance_intelligence import GovernanceIntelligence
from src.governed_execution_orchestrator import GovernedExecutionOrchestrator
from src.governed_execution_orchestrator import GovernedExecutionStore
from src.o45_execution_service import ExecutionService
from src.outcome_intelligence_runtime import OutcomeIntelligenceRuntime
from src.outcome_intelligence_store import OutcomeIntelligenceStore
from src.receipt_store import ExecutionReceiptStore
from src.tool_registry import ToolRegistry


def main():
    with tempfile.TemporaryDirectory() as td:
        gov = GovernanceIntelligence(os.path.join(td, "gov.sqlite3"))
        registry = ToolRegistry()
        calls = []

        def echo(payload):
            calls.append(dict(payload))
            return {"ok": True, "value": payload["value"]}

        registry.register("internal.echo", echo, version="1.0.0")
        receipts = ExecutionReceiptStore(os.path.join(td, "exec.sqlite3"))
        execution = ExecutionService(gov, registry, receipts, worker_id="OIL-E2E")
        geo = GovernedExecutionStore(os.path.join(td, "geo.sqlite3"))
        obs_store = ExecutionObservabilityStore(os.path.join(td, "obs.sqlite3"))
        obs = ExecutionObservability(obs_store)
        orch = GovernedExecutionOrchestrator(execution, geo, obs)
        assessments = OutcomeIntelligenceStore(
            os.path.join(td, "outcome_intelligence.sqlite3")
        )
        runtime = OutcomeIntelligenceRuntime(obs_store, assessments)

        plan = {
            "status": "RECOMMEND",
            "project_id": "P-OIL-E2E",
            "plan_id": "UDI-OIL-E2E",
            "selected_route": {
                "provider": "internal",
                "tool": "internal.echo",
                "score": 1.0,
            },
            "decision_basis": {
                "uncertainty": "LOW",
                "reliability": "STRONG",
            },
            "governance_required": False,
        }

        intent = ExecutionIntentPlanner.build_intent(
            decision_plan=plan,
            action="read_only_inspection",
            payload={"value": "real-trace"},
            project_id="P-OIL-E2E",
            run_id="R-OIL-E2E",
            requested_by="operator",
            context={
                "environment": "offline",
                "confidence": "high",
                "evidence_refs": ["SRC-OIL-E2E"],
                "evidence_boundary": "local_evidence_supported",
            },
        )

        orch.submit_intent(intent, expected_project_id="P-OIL-E2E")
        done = orch.drive(intent["intent_id"])
        assert done["status"] == "SUCCEEDED"
        assert calls == [{"value": "real-trace"}]

        trace = obs.for_intent(intent["intent_id"])
        out = runtime.assess_trace(
            trace["trace_id"],
            target_status="MET",
            evidence_refs=["EVID-OIL-E2E-1", "EVID-OIL-E2E-2"],
            confidence="high",
        )

        assert out["assessment"]["outcome_quality"] == "FULL_SUCCESS"
        assert out["assessment"]["decision_quality"] == "SOUND_DECISION"
        assert out["assessment"]["learning_signal"] == "POSITIVE_CALIBRATION"
        assert out["persistence"]["status"] == "RECORDED"
        assert out["o43_handoff_ready"] is True
        assert out["o43_lesson"]["decision"] == "GO"
        assert (
            out["o43_lesson"]["provenance"]["trace_id"]
            == trace["trace_id"]
        )

        replay = runtime.assess_trace(
            trace["trace_id"],
            target_status="MET",
            evidence_refs=["EVID-OIL-E2E-1", "EVID-OIL-E2E-2"],
            confidence="high",
        )
        assert replay["persistence"]["status"] == "IDEMPOTENT_REPLAY"

        print("V14_TRACE_TO_V15_ASSESSMENT PASS")
        print("V15_ASSESSMENT_PERSISTENCE PASS")
        print("V15_TO_O43_HANDOFF PASS")
        print("V15_END_TO_END_IDEMPOTENCY PASS")
        print(
            {
                "trace_id": trace["trace_id"],
                "assessment_id": out["assessment"]["assessment_id"],
                "learning_signal": out["assessment"]["learning_signal"],
                "o43_decision": out["o43_lesson"]["decision"],
                "replay_status": replay["persistence"]["status"],
            }
        )
        print("ALL V1.5 END-TO-END CHECKS PASSED.")

        orch.close()
        execution.close()
        gov.close()
        assessments.close()


if __name__ == "__main__":
    main()
