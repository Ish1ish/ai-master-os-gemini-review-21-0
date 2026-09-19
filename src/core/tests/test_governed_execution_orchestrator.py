import os
import tempfile
import unittest

from src.execution_intent_planner import ExecutionIntentPlanner
from src.governance_intelligence import GovernanceIntelligence
from src.governed_execution_orchestrator import GovernedExecutionOrchestrator, GovernedExecutionStore
from src.o45_execution_service import ExecutionService
from src.receipt_store import ExecutionReceiptStore
from src.tool_registry import ToolRegistry


class TestGovernedExecutionOrchestrator(unittest.TestCase):
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
        self.execution = ExecutionService(self.gov, self.registry, self.receipts, worker_id="GEO-W1")
        self.store = GovernedExecutionStore(os.path.join(self.tmp.name, "geo.sqlite3"))
        self.orch = GovernedExecutionOrchestrator(self.execution, self.store)
        self.intent = self._intent()

    def tearDown(self):
        self.orch.close(); self.execution.close(); self.gov.close(); self.tmp.cleanup()

    def _intent(self, **changes):
        plan = {
            "status": "RECOMMEND",
            "project_id": "P1",
            "plan_id": "UDI-P1",
            "selected_route": {"provider": "internal", "tool": "internal.echo", "score": 1.2},
            "decision_basis": {"uncertainty": "LOW", "reliability": "STRONG"},
            "governance_required": False,
        }
        data = dict(
            decision_plan=plan,
            action="read_only_inspection",
            payload={"value": "hello"},
            project_id="P1",
            run_id="R1",
            requested_by="operator",
            context={"environment": "offline", "confidence": "high", "evidence_refs": ["SRC-1", "SRC-2"], "evidence_boundary": "local_evidence_supported"},
        )
        data.update(changes)
        return ExecutionIntentPlanner.build_intent(**data)

    def test_auto_allowed_intent_executes_once(self):
        out = self.orch.submit_intent(self.intent, expected_project_id="P1")
        self.assertEqual(out["status"], "READY")
        done = self.orch.drive(self.intent["intent_id"])
        self.assertEqual(done["status"], "SUCCEEDED")
        self.assertEqual(self.calls, [{"value": "hello"}])

    def test_intent_replay_returns_same_execution(self):
        first = self.orch.submit_intent(self.intent)
        second = self.orch.submit_intent(self.intent)
        self.assertEqual(second["status"], "IDEMPOTENT_REPLAY")
        self.assertEqual(second["execution"]["execution_id"], first["execution"]["execution_id"])

    def test_consequential_intent_waits_for_human_approval(self):
        intent = self._intent(action="publish_public_content")
        out = self.orch.submit_intent(intent)
        self.assertEqual(out["status"], "WAITING_HUMAN_APPROVAL")
        driven = self.orch.drive(intent["intent_id"])
        self.assertEqual(driven["status"], "WAITING_HUMAN_APPROVAL")
        self.assertEqual(self.calls, [])

        execution = out["execution"]
        self.gov.decide(execution["approval_id"], {"principal_id": "approver", "roles": ["approver"]}, "APPROVED", "reviewed")
        resumed = self.orch.approve_and_drive(intent["intent_id"])
        self.assertEqual(resumed["status"], "SUCCEEDED")
        self.assertEqual(self.calls, [{"value": "hello"}])

    def test_refine_intent_is_blocked_before_submission(self):
        plan = dict(self.intent)
        plan["status"] = "REFINE"
        out = self.orch.submit_intent(plan)
        self.assertEqual(out["status"], "BLOCKED")
        self.assertEqual(out["reason"], "intent_not_planned")
        self.assertEqual(self.calls, [])

    def test_request_payload_tamper_is_blocked(self):
        tampered = dict(self.intent)
        tampered["execution_request"] = dict(self.intent["execution_request"])
        tampered["execution_request"]["payload"] = {"value": "tampered"}
        out = self.orch.submit_intent(tampered)
        self.assertEqual(out["status"], "BLOCKED")
        self.assertEqual(out["reason"], "request_payload_binding_mismatch")

    def test_idempotency_conflict_is_detected(self):
        first = self.orch.submit_intent(self.intent)
        tampered = self._intent(payload={"value": "different"})
        tampered["intent_id"] = self.intent["intent_id"]
        tampered["execution_request"]["idempotency_key"] = self.intent["execution_request"]["idempotency_key"]
        out = self.orch.submit_intent(tampered)
        self.assertEqual(out["status"], "CONFLICT")
        self.assertEqual(first["execution"]["execution_id"], self.store.get(self.intent["intent_id"])["execution_id"])

    def test_governance_authority_cannot_be_downgraded(self):
        tampered = dict(self.intent, governance_authority="DISABLED")
        out = self.orch.submit_intent(tampered)
        self.assertEqual(out["status"], "BLOCKED")
        self.assertEqual(out["reason"], "governance_authority_invalid")

    def test_unknown_tool_fails_closed_without_handler(self):
        unknown = self._intent()
        unknown["tool_name"] = "missing.tool"
        unknown["execution_request"] = dict(unknown["execution_request"], tool_name="missing.tool")
        out = self.orch.submit_intent(unknown)
        self.assertEqual(out["status"], "BLOCK")
        self.assertEqual(self.calls, [])

    def test_audit_binding_is_persistent(self):
        out = self.orch.submit_intent(self.intent)
        events = self.orch.events(self.intent["intent_id"])
        self.assertTrue(events)
        self.assertEqual(events[0]["event_type"], "SUBMITTED")
        self.assertEqual(events[0]["execution_id"], out["execution"]["execution_id"])

    def test_retry_and_recovery_boundary(self):
        out = self.orch.submit_intent(self.intent)
        execution_id = out["execution"]["execution_id"]
        self.receipts.update_state(execution_id, "RECOVERY_REQUIRED", error={"code": "test"})
        driven = self.orch.drive(self.intent["intent_id"])
        self.assertEqual(driven["status"], "RECOVERY_REQUIRED")

    def test_expected_project_mismatch_is_blocked(self):
        out = self.orch.submit_intent(self.intent, expected_project_id="OTHER")
        self.assertEqual(out["status"], "BLOCKED")
        self.assertEqual(out["reason"], "project_mismatch")


if __name__ == "__main__":
    unittest.main()
