# PATCH_02_O45_UNIFIED_BRIDGE_V8_TEST_ALIGNMENT
# PATCH_02_O45_UNIFIED_BRIDGE_V7_TEST_ALIGNMENT
import tempfile
import unittest

from unified_runtime.integrated_runtime import RealUnifiedRuntime


class TestPatch02O45UnifiedBridge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = RealUnifiedRuntime(self.tmp.name)
        self.calls = []

        def echo(payload):
            self.calls.append(dict(payload))
            return {"ok": True, "value": payload.get("value")}

        self.runtime.register_execution_tool(
            "internal.echo",
            echo,
            version="1.0.0",
        )

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    _DEFAULT_PRINCIPAL = {
        "status": "AUTHENTICATED",
        "authenticated": True,
        "principal": "operator-01",
        "scopes": ["run:submit", "job:execute"],
        "roles": ["operator"],
        "auth_method": "test",
    }

    def _run(self, *, action="read_only_inspection", principal=_DEFAULT_PRINCIPAL, tool_name="internal.echo"):
        return self.runtime.run(
            run_id="PATCH02-R1",
            project_id="PATCH02-P1",
            strategy_id="PATCH02-S1",
            intent="Validate the governed execution bridge",
            goal="Prove O45 receives an explicit execution contract",
            audience="internal",
            evidence={
                "sample_size": 10,
                "evidence_refs": ["PATCH02-EV-1"],
                "metrics": {"problem_confirmed": 8, "pilot_interest": 4},
            },
            principal=principal,
            execution_contract={
                "action": action,
                "tool_name": tool_name,
                "payload": {"value": "bridge-check"},
                "context": {
                    "confidence": "high",
                    "evidence_refs": ["PATCH02-EV-1"],
                    "evidence_boundary": "local_evidence_supported",
                },
            },
        )

    def test_explicit_contract_reaches_o45_without_udi_tool_mapping(self):
        result = self._run()
        governed = result["governed_execution"]

        self.assertEqual(governed["status"], "READY")
        self.assertEqual(governed["intent"]["requested_by"], "operator-01")
        self.assertEqual(governed["intent"]["action"], "read_only_inspection")
        self.assertEqual(governed["intent"]["tool_name"], "internal.echo")
        self.assertEqual(
            governed["intent"]["decision_plan_id"],
            result["stages"]["DECISION"]["plan_id"],
        )
        self.assertEqual(
            result["stages"]["DECISION"]["selected_route"]["tool"],
            "decision-intelligence",
        )
        self.assertEqual(governed["submission"]["execution"]["state"], "READY")
        self.assertEqual(self.calls, [])

    def test_consequential_contract_waits_for_human_approval(self):
        result = self._run(action="publish_public_content")
        governed = result["governed_execution"]

        self.assertEqual(governed["status"], "WAITING_HUMAN_APPROVAL")
        self.assertEqual(
            governed["submission"]["execution"]["state"],
            "AWAITING_APPROVAL",
        )
        self.assertTrue(governed["submission"]["execution"]["approval_id"])
        self.assertEqual(self.calls, [])

    def test_missing_principal_fails_closed_before_o45_submission(self):
        result = self._run(principal={})
        governed = result["governed_execution"]

        self.assertEqual(governed["status"], "BLOCKED")
        self.assertEqual(governed["reason"], "principal_required")
        self.assertEqual(self.calls, [])

    def test_action_and_tool_name_must_remain_distinct(self):
        result = self._run(action="internal.echo", tool_name="internal.echo")
        governed = result["governed_execution"]

        self.assertEqual(governed["status"], "BLOCKED")
        self.assertEqual(
            governed["reason"],
            "action_tool_name_must_be_distinct",
        )
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
