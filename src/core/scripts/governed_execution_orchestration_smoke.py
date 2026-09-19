import os
import tempfile

from src.execution_intent_planner import ExecutionIntentPlanner
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
            calls.append(payload)
            return {"ok": True, "value": payload["value"]}

        registry.register("internal.echo", echo, version="1.0.0")
        receipts = ExecutionReceiptStore(os.path.join(td, "exec.sqlite3"))
        execution = ExecutionService(gov, registry, receipts, worker_id="GEO-SMOKE")
        store = GovernedExecutionStore(os.path.join(td, "geo.sqlite3"))
        orch = GovernedExecutionOrchestrator(execution, store)

        plan = {
            "status": "RECOMMEND",
            "project_id": "GEO-DEMO",
            "plan_id": "UDI-GEO-001",
            "selected_route": {"provider": "internal", "tool": "internal.echo", "score": 1.1},
            "decision_basis": {"uncertainty": "LOW", "reliability": "STRONG"},
            "governance_required": False,
        }
        intent = ExecutionIntentPlanner.build_intent(
            decision_plan=plan,
            action="read_only_inspection",
            payload={"value": "governed"},
            project_id="GEO-DEMO",
            run_id="R-GEO-001",
            requested_by="operator",
            context={"environment": "offline", "confidence": "high", "evidence_refs": ["SRC-1", "SRC-2"], "evidence_boundary": "local_evidence_supported"},
        )
        submitted = orch.submit_intent(intent, expected_project_id="GEO-DEMO")
        assert submitted["status"] == "READY"
        done = orch.drive(intent["intent_id"])
        assert done["status"] == "SUCCEEDED"
        assert calls == [{"value": "governed"}]

        replay = orch.submit_intent(intent)
        assert replay["status"] == "IDEMPOTENT_REPLAY"
        assert replay["execution"]["execution_id"] == done["execution"]["execution_id"]

        reviewed = ExecutionIntentPlanner.build_intent(
            decision_plan=plan,
            action="publish_public_content",
            payload={"value": "public"},
            project_id="GEO-DEMO",
            run_id="R-GEO-002",
            requested_by="operator",
            context={"environment": "offline", "confidence": "high", "evidence_refs": ["SRC-1", "SRC-2"], "evidence_boundary": "local_evidence_supported"},
        )
        waiting = orch.submit_intent(reviewed)
        assert waiting["status"] == "WAITING_HUMAN_APPROVAL"
        assert calls == [{"value": "governed"}]

        print("GOVERNED EXECUTION ORCHESTRATION SMOKE PASS")
        print({
            "auto_status": done["status"],
            "replay_status": replay["status"],
            "approval_status": waiting["status"],
            "external_calls": len(calls),
            "execution_id": done["execution"]["execution_id"],
            "intent_id": intent["intent_id"],
        })
        print("GOVERNED EXECUTION BOUNDARY PASS")
        print("ALL GOVERNED EXECUTION ORCHESTRATION CHECKS PASSED.")

        orch.close(); execution.close(); gov.close()


if __name__ == "__main__":
    main()
