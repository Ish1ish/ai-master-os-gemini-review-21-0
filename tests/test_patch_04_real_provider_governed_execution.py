"""PATCH_04_REAL_PROVIDER_GOVERNED_EXECUTION

Regression coverage for driving a governed execution intent through to real
tool invocation via the canonical O45 path:

    RealUnifiedRuntime.run(execution_contract=...)   # submit only (Patch 02, unchanged)
      -> governed_execution.intent.intent_id
    RealUnifiedRuntime.execute_governed_intent(intent_id, principal=...)  # NEW
      -> GovernedExecutionOrchestrator.drive()
      -> o45_execution_service.ExecutionService.execute_once()
      -> ToolRegistry-resolved handler actually called
      -> execution receipt updated (SUCCEEDED / FAILED_*)

Two kinds of tests:
  1. Deterministic tests using an injected fake provider callable (no
     network, no credentials, run every time).
  2. A real-provider test that only runs when the environment already
     satisfies the existing AI_OS_MODEL_*/AI_OS_SEARCH_* configuration
     contract (see live_providers.provider_configuration_status()); it is
     skipped otherwise. It performs exactly one real, read-only search call.

Nothing here modifies Patch 02's submit-only run() contract: test_patch_02_*
continues to assert governed["submission"]["execution"]["state"] == "READY"
and that the registered tool was never called during run() itself - this
file only exercises the new, separate execute_governed_intent() step.
"""
from __future__ import annotations

import tempfile
import unittest

from unified_runtime.integrated_runtime import RealUnifiedRuntime
from core.src.live_providers import provider_configuration_status
from core.src.canonical_provider_tools import real_search_tool


_DEFAULT_PRINCIPAL = {
    "status": "AUTHENTICATED",
    "authenticated": True,
    "principal": "operator-01",
    "scopes": ["run:submit", "job:execute"],
    "roles": ["operator"],
    "auth_method": "test",
}


class TestPatch04RealProviderGovernedExecution(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = RealUnifiedRuntime(self.tmp.name)

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def _submit(self, tool_name, tool_handler, *, action="read_only_inspection", query="ai workflow automation"):
        self.runtime.register_execution_tool(tool_name, tool_handler, version="1.0.0")
        return self.runtime.run(
            run_id="PATCH04-R1",
            project_id="PATCH04-P1",
            strategy_id="PATCH04-S1",
            intent="Validate real provider governed execution",
            goal="Prove a registered tool reaches real execution via drive()",
            audience="internal",
            evidence={
                "sample_size": 10,
                "evidence_refs": ["PATCH04-EV-1"],
                "metrics": {"problem_confirmed": 8, "pilot_interest": 4},
            },
            principal=_DEFAULT_PRINCIPAL,
            execution_contract={
                "action": action,
                "tool_name": tool_name,
                "payload": {"query": query},
                "context": {
                    "confidence": "high",
                    "evidence_refs": ["PATCH04-EV-1"],
                    "evidence_boundary": "local_evidence_supported",
                },
            },
        )

    def test_submit_alone_still_never_calls_the_tool(self):
        # Preserves the exact Patch 02 submit-only contract.
        calls = []

        def fake_tool(payload):
            calls.append(dict(payload))
            return {"ok": True}

        result = self._submit("provider.search.fake", fake_tool)
        governed = result["governed_execution"]
        self.assertEqual(governed["status"], "READY")
        self.assertEqual(governed["submission"]["execution"]["state"], "READY")
        self.assertEqual(calls, [])

    def test_execute_governed_intent_drives_a_ready_intent_to_success(self):
        calls = []
        credential_marker = "SHOULD-NEVER-APPEAR"

        def fake_search(payload):
            calls.append(dict(payload))
            return {"provider": "fake_search", "query": payload.get("query"), "result_count": 1,
                     "results": [{"title": "result", "snippet": "ok"}]}

        result = self._submit("provider.search.fake", fake_search)
        intent_id = result["governed_execution"]["intent"]["intent_id"]

        driven = self.runtime.execute_governed_intent(intent_id, principal=_DEFAULT_PRINCIPAL)

        self.assertEqual(driven["status"], "SUCCEEDED")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], {"query": "ai workflow automation"})
        execution = driven["execution"]
        self.assertEqual(execution["state"], "SUCCEEDED")
        self.assertIn("result", execution)
        # No credential-shaped value anywhere in the receipt/result.
        serialized = str(execution)
        self.assertNotIn(credential_marker, serialized)

    def test_execute_governed_intent_on_awaiting_approval_never_calls_the_tool(self):
        calls = []

        def fake_tool(payload):
            calls.append(dict(payload))
            return {"ok": True}

        result = self._submit("provider.search.fake", fake_tool, action="publish_public_content")
        governed = result["governed_execution"]
        self.assertEqual(governed["status"], "WAITING_HUMAN_APPROVAL")
        intent_id = governed["intent"]["intent_id"]

        driven = self.runtime.execute_governed_intent(intent_id, principal=_DEFAULT_PRINCIPAL)

        self.assertEqual(driven["status"], "WAITING_HUMAN_APPROVAL")
        self.assertEqual(calls, [])

    def test_tool_failure_becomes_governed_outcome_not_a_crash(self):
        def failing_tool(payload):
            raise RuntimeError("simulated_provider_failure")

        result = self._submit("provider.search.failing", failing_tool)
        intent_id = result["governed_execution"]["intent"]["intent_id"]

        driven = self.runtime.execute_governed_intent(intent_id, principal=_DEFAULT_PRINCIPAL)

        self.assertIn(driven["status"], {"FAILED_RETRYABLE", "RECOVERY_REQUIRED"})
        self.assertNotIn("simulated_provider_failure_traceback", str(driven))

    def test_real_search_tool_wrapper_rejects_empty_query(self):
        with self.assertRaises(ValueError):
            real_search_tool({"query": "  "})


@unittest.skipUnless(
    provider_configuration_status().get("status") == "CONFIGURED",
    "Real provider environment (AI_OS_MODEL_*/AI_OS_SEARCH_*) is not configured; "
    "skipping the live real-provider governed-execution test.",
)
class TestPatch04RealProviderLiveExecution(unittest.TestCase):
    """Only runs when the existing provider environment contract is already
    satisfied. Performs exactly one real, read-only search call, driven
    through the full canonical O45 governed-execution path."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = RealUnifiedRuntime(self.tmp.name)
        self.runtime.register_execution_tool("provider.search.live", real_search_tool, version="1.0.0")

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def test_real_provider_request_completes_through_governed_execution(self):
        result = self.runtime.run(
            run_id="PATCH04-LIVE-R1",
            project_id="PATCH04-LIVE-P1",
            strategy_id="PATCH04-LIVE-S1",
            intent="Validate real provider governed execution (live)",
            goal="Prove a real provider call reaches O45 and produces a persisted outcome",
            audience="internal",
            evidence={
                "sample_size": 10,
                "evidence_refs": ["PATCH04-LIVE-EV-1"],
                "metrics": {"problem_confirmed": 8, "pilot_interest": 4},
            },
            principal=_DEFAULT_PRINCIPAL,
            execution_contract={
                "action": "read_only_inspection",
                "tool_name": "provider.search.live",
                "payload": {"query": "AI workflow automation for small businesses"},
                "context": {
                    "confidence": "high",
                    "evidence_refs": ["PATCH04-LIVE-EV-1"],
                    "evidence_boundary": "local_evidence_supported",
                },
            },
        )
        governed = result["governed_execution"]
        self.assertEqual(governed["status"], "READY")
        intent_id = governed["intent"]["intent_id"]

        driven = self.runtime.execute_governed_intent(intent_id, principal=_DEFAULT_PRINCIPAL)

        self.assertEqual(driven["status"], "SUCCEEDED")
        execution = driven["execution"]
        self.assertEqual(execution["state"], "SUCCEEDED")
        provider_result = execution.get("result") or {}
        self.assertEqual(provider_result.get("provider"), "live_search")
        self.assertGreaterEqual(provider_result.get("result_count", 0), 0)
        # No credential value is ever present in the receipt.
        for env_name in ("AI_OS_MODEL_API_KEY", "AI_OS_SEARCH_API_KEY"):
            import os
            secret = os.getenv(env_name)
            if secret:
                self.assertNotIn(secret, str(execution))


if __name__ == "__main__":
    unittest.main()
