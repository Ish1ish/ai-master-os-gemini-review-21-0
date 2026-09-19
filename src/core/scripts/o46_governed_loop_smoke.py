import os
import tempfile

from src.governance_intelligence import GovernanceIntelligence
from src.o45_execution_service import ExecutionService
from src.o46_orchestrator import GovernedAutonomousLoop
from src.o46_store import CycleStore
from src.receipt_store import ExecutionReceiptStore
from src.tool_registry import ToolRegistry


def main():
    with tempfile.TemporaryDirectory() as td:
        gov = GovernanceIntelligence(os.path.join(td, "gov.sqlite3"))
        registry = ToolRegistry()
        calls = []

        def echo(payload):
            calls.append(payload)
            return {"ok": True, "echo": payload["value"]}

        registry.register("internal.echo", echo, version="1.0.0")
        receipts = ExecutionReceiptStore(os.path.join(td, "exec.sqlite3"))
        execution = ExecutionService(gov, registry, receipts, worker_id="O46-SMOKE")
        loop = GovernedAutonomousLoop(
            execution_service=execution,
            cycle_store=CycleStore(os.path.join(td, "cycles.sqlite3")),
        )
        context = {"confidence": "high", "evidence_refs": ["SRC-1", "SRC-2"], "evidence_boundary": "local_evidence_supported"}
        plan = {
            "version": "O46-v1.0",
            "actions": [{"action": "read_only_inspection", "tool_name": "internal.echo", "payload": {"value": "smoke"}, "idempotency_key": "O46-A1"}],
        }
        out = loop.start_cycle(project_id="P-O46", run_id="R-O46", plan=plan, idempotency_key="O46-C1", requested_by="operator", context=context)
        assert out["status"] == "COMPLETE"
        assert calls == [{"value": "smoke"}]
        replay = loop.start_cycle(project_id="P-O46", run_id="R-O46", plan=plan, idempotency_key="O46-C1", requested_by="operator", context=context)
        assert replay["status"] == "IDEMPOTENT_REPLAY"
        print({"status": "PASS", "cycle": out["cycle"]["cycle_id"], "replay": replay["status"]})
        loop.close(); execution.close(); gov.close()


if __name__ == "__main__":
    main()
