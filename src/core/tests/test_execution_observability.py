import os
import tempfile
import unittest

from src.execution_intent_planner import ExecutionIntentPlanner
from src.execution_observability import ExecutionObservability, ExecutionObservabilityStore, trace_id
from src.governance_intelligence import GovernanceIntelligence
from src.governed_execution_orchestrator import GovernedExecutionOrchestrator, GovernedExecutionStore
from src.o45_execution_service import ExecutionService
from src.receipt_store import ExecutionReceiptStore
from src.tool_registry import ToolRegistry


class TestExecutionObservability(unittest.TestCase):
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
        self.execution = ExecutionService(self.gov, self.registry, self.receipts, worker_id="EOE-W1")
        self.geo_store = GovernedExecutionStore(os.path.join(self.tmp.name, "geo.sqlite3"))
        self.obs_store = ExecutionObservabilityStore(os.path.join(self.tmp.name, "obs.sqlite3"))
        self.obs = ExecutionObservability(self.obs_store)
        self.orch = GovernedExecutionOrchestrator(self.execution, self.geo_store, self.obs)
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

    def test_trace_links_decision_intent_execution_outcome(self):
        out = self.orch.submit_intent(self.intent)
        done = self.orch.drive(self.intent["intent_id"])
        self.assertEqual(done["status"], "SUCCEEDED")
        trace = self.obs.for_intent(self.intent["intent_id"])
        self.assertIsNotNone(trace)
        self.assertEqual(trace["decision_plan_id"], "UDI-P1")
        self.assertEqual(trace["intent_id"], self.intent["intent_id"])
        self.assertEqual(trace["execution_id"], out["execution"]["execution_id"])
        self.assertEqual(trace["outcome_status"], "SUCCEEDED")
        event_types = [e["event_type"] for e in trace["events"]]
        self.assertIn("DECISION_RECORDED", event_types)
        self.assertIn("INTENT_RECORDED", event_types)
        self.assertIn("EXECUTION_SUBMITTED", event_types)
        self.assertIn("EXECUTION_STARTED", event_types)
        self.assertIn("EXECUTION_FINISHED", event_types)
        self.assertIn("OUTCOME_RECORDED", event_types)

    def test_outcome_evidence_is_idempotent(self):
        out = self.obs.record_outcome(
            project_id="P1", run_id="R1", decision_plan_id="UDI-P1", intent_id="I1", execution_id="E1",
            expected_status="RECOMMEND", actual_status="SUCCEEDED", outcome_status="SUCCEEDED", success=True,
            evidence_refs=["EVID-1"], result={"ok": True}, evidence_key="OE-FIXED",
        )
        replay = self.obs.record_outcome(
            project_id="P1", run_id="R1", decision_plan_id="UDI-P1", intent_id="I1", execution_id="E1",
            expected_status="RECOMMEND", actual_status="SUCCEEDED", outcome_status="SUCCEEDED", success=True,
            evidence_refs=["EVID-1"], result={"ok": True}, evidence_key="OE-FIXED",
        )
        self.assertEqual(out["status"], "RECORDED")
        self.assertEqual(replay["status"], "IDEMPOTENT_REPLAY")

    def test_trace_id_is_deterministic(self):
        a = trace_id(project_id="P", run_id="R", decision_plan_id="D", intent_id="I", execution_id="E")
        b = trace_id(project_id="P", run_id="R", decision_plan_id="D", intent_id="I", execution_id="E")
        self.assertEqual(a, b)

    def test_missing_trace_is_rejected(self):
        with self.assertRaises(KeyError):
            self.obs_store.trace("TRC-MISSING")


if __name__ == "__main__":
    unittest.main()
