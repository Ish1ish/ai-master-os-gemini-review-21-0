import os
import tempfile

from src.execution_intent_planner import ExecutionIntentPlanner
from src.execution_observability import ExecutionObservability, ExecutionObservabilityStore
from src.governance_intelligence import GovernanceIntelligence
from src.governed_execution_orchestrator import GovernedExecutionOrchestrator, GovernedExecutionStore
from src.o45_execution_service import ExecutionService
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
        execution = ExecutionService(gov, registry, receipts, worker_id="EOE-SMOKE")
        geo = GovernedExecutionStore(os.path.join(td, "geo.sqlite3"))
        obs = ExecutionObservability(ExecutionObservabilityStore(os.path.join(td, "obs.sqlite3")))
        orch = GovernedExecutionOrchestrator(execution, geo, obs)

        plan = {
            "status": "RECOMMEND", "project_id": "EOE-DEMO", "plan_id": "UDI-EOE-001",
            "selected_route": {"provider": "internal", "tool": "internal.echo", "score": 1.1},
            "decision_basis": {"uncertainty": "LOW", "reliability": "STRONG"}, "governance_required": False,
        }
        intent = ExecutionIntentPlanner.build_intent(
            decision_plan=plan, action="read_only_inspection", payload={"value": "observed"},
            project_id="EOE-DEMO", run_id="R-EOE-001", requested_by="operator",
            context={"environment": "offline", "confidence": "high", "evidence_refs": ["SRC-1", "SRC-2"], "evidence_boundary": "local_evidence_supported"},
        )
        submitted = orch.submit_intent(intent, expected_project_id="EOE-DEMO")
        assert submitted["status"] == "READY"
        done = orch.drive(intent["intent_id"])
        assert done["status"] == "SUCCEEDED"
        trace = obs.for_intent(intent["intent_id"])
        assert trace["decision_plan_id"] == "UDI-EOE-001"
        assert trace["execution_state"] == "SUCCEEDED"
        assert trace["outcome_status"] == "SUCCEEDED"
        assert trace["outcomes"] and trace["outcomes"][0]["success"] is True
        assert calls == [{"value": "observed"}]

        print("EXECUTION OBSERVABILITY SMOKE PASS")
        print({
            "trace_id": trace["trace_id"],
            "decision_plan_id": trace["decision_plan_id"],
            "intent_id": trace["intent_id"],
            "execution_id": trace["execution_id"],
            "decision_status": trace["decision_status"],
            "execution_state": trace["execution_state"],
            "outcome_status": trace["outcome_status"],
            "outcome_success": trace["outcomes"][0]["success"],
            "event_count": len(trace["events"]),
        })
        print("DECISION_TO_OUTCOME_TRACE PASS")
        print("ALL EXECUTION OBSERVABILITY CHECKS PASSED.")
        orch.close(); execution.close(); gov.close()


if __name__ == "__main__":
    main()
