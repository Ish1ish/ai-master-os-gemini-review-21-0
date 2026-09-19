import os
import tempfile
import unittest

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


class TestOutcomeIntelligenceRuntime(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        root = self.td.name

        self.gov = GovernanceIntelligence(os.path.join(root, "gov.sqlite3"))
        self.registry = ToolRegistry()
        self.calls = []

        def echo(payload):
            self.calls.append(dict(payload))
            return {"ok": True, "value": payload["value"]}

        self.registry.register("internal.echo", echo, version="1.0.0")
        self.receipts = ExecutionReceiptStore(os.path.join(root, "exec.sqlite3"))
        self.execution = ExecutionService(
            self.gov, self.registry, self.receipts, worker_id="OIL-E2E"
        )
        self.geo = GovernedExecutionStore(os.path.join(root, "geo.sqlite3"))
        self.obs_store = ExecutionObservabilityStore(
            os.path.join(root, "obs.sqlite3")
        )
        self.obs = ExecutionObservability(self.obs_store)
        self.orch = GovernedExecutionOrchestrator(
            self.execution, self.geo, self.obs
        )
        self.assessment_store = OutcomeIntelligenceStore(
            os.path.join(root, "outcome_intelligence.sqlite3")
        )
        self.runtime = OutcomeIntelligenceRuntime(
            self.obs_store, self.assessment_store
        )

    def tearDown(self):
        self.orch.close()
        self.execution.close()
        self.gov.close()
        self.assessment_store.close()
        self.td.cleanup()

    def _intent(self):
        plan = {
            "status": "RECOMMEND",
            "project_id": "P-E2E",
            "plan_id": "UDI-E2E",
            "selected_route": {
                "provider": "internal",
                "tool": "internal.echo",
                "score": 1.2,
            },
            "decision_basis": {
                "uncertainty": "LOW",
                "reliability": "STRONG",
            },
            "governance_required": False,
        }
        return ExecutionIntentPlanner.build_intent(
            decision_plan=plan,
            action="read_only_inspection",
            payload={"value": "e2e"},
            project_id="P-E2E",
            run_id="R-E2E",
            requested_by="operator",
            context={
                "environment": "offline",
                "confidence": "high",
                "evidence_refs": ["SRC-E2E-1"],
                "evidence_boundary": "local_evidence_supported",
            },
        )

    def test_trace_to_assessment_to_o43_lesson(self):
        intent = self._intent()
        submitted = self.orch.submit_intent(intent)
        self.assertEqual(submitted["status"], "READY")

        done = self.orch.drive(intent["intent_id"])
        self.assertEqual(done["status"], "SUCCEEDED")

        trace = self.obs.for_intent(intent["intent_id"])
        self.assertIsNotNone(trace)

        out = self.runtime.assess_trace(
            trace["trace_id"],
            target_status="MET",
            evidence_refs=["EVID-E2E-1", "EVID-E2E-2"],
            confidence="high",
        )

        self.assertEqual(out["assessment"]["outcome_quality"], "FULL_SUCCESS")
        self.assertEqual(out["assessment"]["decision_quality"], "SOUND_DECISION")
        self.assertEqual(
            out["assessment"]["learning_signal"], "POSITIVE_CALIBRATION"
        )
        self.assertEqual(out["persistence"]["status"], "RECORDED")
        self.assertEqual(out["o43_lesson"]["decision"], "GO")
        self.assertEqual(
            out["o43_lesson"]["provenance"]["trace_id"],
            trace["trace_id"],
        )

    def test_replaying_same_trace_is_idempotent(self):
        intent = self._intent()
        self.orch.submit_intent(intent)
        self.orch.drive(intent["intent_id"])
        trace = self.obs.for_intent(intent["intent_id"])

        args = dict(
            trace_id=trace["trace_id"],
            target_status="MET",
            evidence_refs=["EVID-REPLAY"],
            confidence="high",
        )
        first = self.runtime.assess_trace(**args)
        replay = self.runtime.assess_trace(**args)

        self.assertEqual(first["persistence"]["status"], "RECORDED")
        self.assertEqual(
            replay["persistence"]["status"],
            "IDEMPOTENT_REPLAY",
        )
        self.assertEqual(
            first["assessment"]["assessment_id"],
            replay["assessment"]["assessment_id"],
        )

    def test_unknown_target_blocks_learning_from_real_trace(self):
        intent = self._intent()
        self.orch.submit_intent(intent)
        self.orch.drive(intent["intent_id"])
        trace = self.obs.for_intent(intent["intent_id"])

        out = self.runtime.assess_trace(
            trace["trace_id"],
            target_status="UNKNOWN",
            evidence_refs=["EVID-UNKNOWN"],
            confidence="high",
        )

        self.assertEqual(
            out["assessment"]["learning_signal"],
            "DO_NOT_LEARN",
        )
        self.assertFalse(out["o43_handoff_ready"])
        self.assertIsNone(out["o43_lesson"])


if __name__ == "__main__":
    unittest.main()
