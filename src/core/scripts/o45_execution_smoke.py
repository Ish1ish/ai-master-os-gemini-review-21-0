import os
import tempfile

from src.governance_intelligence import GovernanceIntelligence
from src.receipt_store import ExecutionReceiptStore
from src.tool_registry import ToolRegistry
from src.o45_execution_service import ExecutionService


def main():
    with tempfile.TemporaryDirectory() as td:
        governance = GovernanceIntelligence(os.path.join(td, "governance.sqlite3"))
        registry = ToolRegistry()
        calls = []

        def internal_tool(payload):
            calls.append(payload)
            return {"ok": True, "echo": payload["value"]}

        registry.register("internal.echo", internal_tool, version="1.0.0")
        service = ExecutionService(
            governance,
            registry,
            ExecutionReceiptStore(os.path.join(td, "executions.sqlite3")),
            worker_id="SMOKE-W1",
        )

        ctx = {
            "confidence": "high",
            "evidence_refs": ["SRC-1", "SRC-2"],
            "evidence_boundary": "local_evidence_supported",
        }

        req = service.request(
            project_id="PROJ-O45",
            run_id="RUN-LOW",
            action="read_only_inspection",
            tool_name="internal.echo",
            payload={"value": "hello"},
            context=ctx,
            idempotency_key="IDEMP-001",
            requested_by="operator-01",
        )
        assert req["status"] == "ACCEPTED"
        eid = req["execution"]["execution_id"]
        done = service.execute_once(eid)
        assert done["status"] == "SUCCEEDED"
        assert calls == [{"value": "hello"}]

        replay = service.execute_once(eid)
        assert replay["status"] == "IDEMPOTENT_REPLAY"
        assert len(calls) == 1

        conflict = service.request(
            project_id="PROJ-O45",
            run_id="RUN-LOW",
            action="read_only_inspection",
            tool_name="internal.echo",
            payload={"value": "different"},
            context=ctx,
            idempotency_key="IDEMP-001",
            requested_by="operator-01",
        )
        assert conflict["status"] == "CONFLICT"

        blocked = service.request(
            project_id="PROJ-O45",
            run_id="RUN-BLOCK",
            action="unknown_action",
            tool_name="internal.echo",
            payload={"value": "blocked"},
            context=ctx,
            idempotency_key="IDEMP-002",
            requested_by="operator-01",
        )
        assert blocked["status"] == "ACCEPTED"
        assert blocked["execution"]["state"] == "BLOCKED"
        assert service.execute_once(blocked["execution"]["execution_id"])["status"] == "BLOCKED"

        review = service.request(
            project_id="PROJ-O45",
            run_id="RUN-REVIEW",
            action="publish_public_content",
            tool_name="internal.echo",
            payload={"value": "external"},
            context=ctx,
            idempotency_key="IDEMP-003",
            requested_by="operator-01",
        )
        assert review["execution"]["state"] == "AWAITING_APPROVAL"
        rid = review["execution"]["execution_id"]
        aid = review["execution"]["approval_id"]
        denied = governance.decide(
            aid,
            {"principal_id": "operator-01", "roles": ["operator"]},
            "APPROVED",
            "not authorized",
        )
        assert denied["status"] == "DENY"
        approved = governance.decide(
            aid,
            {"principal_id": "approver-01", "roles": ["approver"]},
            "APPROVED",
            "reviewed",
        )
        assert approved["status"] == "APPROVED"
        ready = service.approve_and_ready(rid)
        assert ready["state"] == "READY"

        print({
            "status": "PASS",
            "auto_allow": "SUCCEEDED",
            "idempotency": "ENFORCED",
            "block": "FAIL_CLOSED",
            "approval": "HUMAN_APPROVED",
            "execution_id": eid,
        })

        service.close()
        governance.close()


if __name__ == "__main__":
    main()
