import os
import tempfile
import unittest

from src.governance_intelligence import GovernanceIntelligence
from src.o45_execution_service import ExecutionService
from src.receipt_store import ExecutionReceiptStore
from src.tool_registry import ToolRegistry
from src.o46_orchestrator import GovernedAutonomousLoop
from src.o46_store import CycleStore


class FakeExperimentService:
    def __init__(self):
        self.evidence = []
        self.calls = 0

    def record_evidence(self, experiment_id, evidence):
        self.evidence.append((experiment_id, evidence))
        return {"status": "OK", "evidence": evidence}

    def evaluate(self, experiment_id):
        self.calls += 1
        return {
            "evaluation": {
                "decision": "GO",
                "confidence": "high",
                "summary": "thresholds met",
                "evidence_refs": ["EVID-1"],
            }
        }


class TestO46GovernedLoop(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.gov = GovernanceIntelligence(os.path.join(self.tmp.name, "gov.sqlite3"))
        self.registry = ToolRegistry()
        self.calls = []

        def echo(payload):
            self.calls.append(dict(payload))
            return {"ok": True, "value": payload.get("value")}

        self.registry.register("internal.echo", echo, version="1.0.0")
        self.receipts = ExecutionReceiptStore(os.path.join(self.tmp.name, "exec.sqlite3"))
        self.exec = ExecutionService(self.gov, self.registry, self.receipts, worker_id="O46-W1")
        self.cycles = CycleStore(os.path.join(self.tmp.name, "cycles.sqlite3"))
        self.exps = FakeExperimentService()
        self.loop = GovernedAutonomousLoop(
            execution_service=self.exec,
            cycle_store=self.cycles,
            experiment_service=self.exps,
        )

    def tearDown(self):
        self.exec.close(); self.gov.close(); self.cycles.close(); self.tmp.cleanup()

    def base_plan(self, **extra):
        plan = {
            "version": "O46-v1.0",
            "actions": [
                {
                    "action": "read_only_inspection",
                    "tool_name": "internal.echo",
                    "payload": {"value": "hello"},
                    "idempotency_key": "ACT-1",
                }
            ],
        }
        plan.update(extra)
        return plan

    def test_auto_allowed_cycle_completes(self):
        out = self.loop.start_cycle(
            project_id="P1", run_id="R1", plan=self.base_plan(),
            idempotency_key="CYCLE-1", requested_by="operator",
            context={"confidence": "high", "evidence_refs": ["SRC-1", "SRC-2"], "evidence_boundary": "local_evidence_supported"},
        )
        self.assertEqual(out["status"], "COMPLETE")
        self.assertEqual(self.calls, [{"value": "hello"}])
        self.assertEqual(len(self.loop.events(out["cycle"]["cycle_id"])), 4)

    def test_cycle_idempotency_replays_same_cycle(self):
        first = self.loop.start_cycle(
            project_id="P1", run_id="R1", plan=self.base_plan(),
            idempotency_key="CYCLE-2", requested_by="operator",
            context={"confidence": "high", "evidence_refs": ["SRC-1", "SRC-2"], "evidence_boundary": "local_evidence_supported"},
        )
        second = self.loop.start_cycle(
            project_id="P1", run_id="R1", plan=self.base_plan(),
            idempotency_key="CYCLE-2", requested_by="operator",
        )
        self.assertEqual(second["status"], "IDEMPOTENT_REPLAY")
        self.assertEqual(second["cycle"]["cycle_id"], first["cycle"]["cycle_id"])
        self.assertEqual(len(self.calls), 1)

    def test_consequential_action_pauses_for_human_approval(self):
        plan = self.base_plan(actions=[{
            "action": "publish_public_content",
            "tool_name": "internal.echo",
            "payload": {"value": "public"},
            "idempotency_key": "ACT-REV-1",
        }])
        out = self.loop.start_cycle(
            project_id="P1", run_id="R2", plan=plan,
            idempotency_key="CYCLE-3", requested_by="operator",
            context={"confidence": "high", "evidence_refs": ["SRC-1", "SRC-2"], "evidence_boundary": "local_evidence_supported"},
        )
        self.assertEqual(out["status"], "WAITING_HUMAN_APPROVAL")
        self.assertEqual(self.calls, [])
        cycle = out["cycle"]
        self.assertTrue(cycle["execution_ids"])

        eid = cycle["execution_ids"][0]
        receipt = self.receipts.get(eid)
        self.gov.decide(receipt["approval_id"], {"principal_id": "approver", "roles": ["approver"]}, "APPROVED", "reviewed")
        resumed = self.loop.resume(cycle["cycle_id"])
        self.assertEqual(resumed["status"], "COMPLETE")
        self.assertEqual(self.calls, [{"value": "public"}])

    def test_unknown_action_blocks_without_tool_call(self):
        plan = self.base_plan(actions=[{
            "action": "totally_unknown",
            "tool_name": "internal.echo",
            "payload": {"value": "x"},
            "idempotency_key": "ACT-BLOCK-1",
        }])
        out = self.loop.start_cycle(
            project_id="P1", run_id="R3", plan=plan,
            idempotency_key="CYCLE-4", requested_by="operator",
            context={"confidence": "high", "evidence_refs": ["SRC-1", "SRC-2"], "evidence_boundary": "local_evidence_supported"},
        )
        self.assertEqual(out["status"], "BLOCKED")
        self.assertEqual(self.calls, [])

    def test_evidence_drives_learning_route(self):
        plan = self.base_plan(experiment_id="EXP-1")
        out = self.loop.start_cycle(
            project_id="P1", run_id="R4", plan=plan,
            idempotency_key="CYCLE-5", requested_by="operator",
            context={"confidence": "high", "evidence_refs": ["SRC-1", "SRC-2"], "evidence_boundary": "local_evidence_supported"},
        )
        self.assertEqual(out["status"], "EVIDENCE_PENDING")
        learned = self.loop.record_evidence_and_learn(
            out["cycle"]["cycle_id"],
            {"sample_size": 10, "metrics": {"success_rate": 0.8}, "evidence_refs": ["EVID-1"], "notes": "measured"},
        )
        self.assertEqual(learned["status"], "COMPLETE")
        self.assertEqual(learned["cycle"]["next_cycle"]["route"], "BOUNDED_NEXT_STEP")
        self.assertEqual(self.exps.calls, 1)

    def test_invalid_plan_is_rejected(self):
        out = self.loop.start_cycle(project_id="P1", run_id="R5", plan={}, idempotency_key="CYCLE-6", requested_by="operator")
        self.assertEqual(out, {"status": "BAD_REQUEST", "reason": "actions_required"})

    def test_duplicate_action_keys_are_rejected(self):
        plan = self.base_plan(actions=[
            {"action": "read_only_inspection", "tool_name": "internal.echo", "payload": {}, "idempotency_key": "DUP"},
            {"action": "read_only_inspection", "tool_name": "internal.echo", "payload": {}, "idempotency_key": "DUP"},
        ])
        out = self.loop.start_cycle(project_id="P1", run_id="R6", plan=plan, idempotency_key="CYCLE-7", requested_by="operator")
        self.assertEqual(out["reason"], "duplicate_action_idempotency_key")


if __name__ == "__main__":
    unittest.main()
