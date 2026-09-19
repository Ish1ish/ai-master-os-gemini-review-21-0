import unittest

from unified_runtime.execution_outcome import UnifiedExecutionOutcomeAdapter


class TestS5ExecutionOutcomeIntegration(unittest.TestCase):
    def setUp(self):
        self.adapter = UnifiedExecutionOutcomeAdapter()
        self.governance_go = {
            "status": "GOVERNED",
            "posture": "PROCEED_TO_EXECUTION_GATE",
        }
        self.governance_refine = {
            "status": "GOVERNED",
            "posture": "REFINE_BEFORE_EXECUTION",
        }

    def test_go_reaches_simulated_execution_and_success_outcome(self):
        result = self.adapter.run(
            self.governance_go,
            run_id="UR-001",
            project_id="demo",
            action_key="validate-core-workflow",
        )
        self.assertEqual(result["execution_status"], "SUCCEEDED")
        self.assertEqual(result["outcome_status"], "SUCCESS")
        self.assertEqual(result["run_id"], "UR-001")
        self.assertTrue(result["outcome_evidence"]["observable"])
        self.assertFalse(result["external_action_executed"])
        self.assertFalse(result["governance_mutation"])

    def test_refine_never_reaches_executor(self):
        called = []
        result = self.adapter.run(
            self.governance_refine,
            run_id="UR-001",
            project_id="demo",
            action_key="validate-core-workflow",
            executor=lambda: called.append(True) or {"status": "SUCCEEDED"},
        )
        self.assertEqual(result["execution_status"], "BLOCKED")
        self.assertEqual(called, [])

    def test_consequential_action_requires_human_gate(self):
        called = []
        result = self.adapter.run(
            self.governance_go,
            run_id="UR-001",
            project_id="demo",
            action_key="publish",
            executor=lambda: called.append(True) or {"status": "SUCCEEDED"},
            consequential=True,
            approval_status="NOT_REQUIRED",
            authorized=True,
        )
        self.assertEqual(result["execution_status"], "BLOCKED")
        self.assertEqual(called, [])
        self.assertFalse(result["external_action_executed"])

    def test_approved_authorized_consequential_action_is_explicit(self):
        result = self.adapter.run(
            self.governance_go,
            run_id="UR-001",
            project_id="demo",
            action_key="publish",
            executor=lambda: {"status": "SUCCEEDED", "output": {"published": "approved-test"}},
            consequential=True,
            approval_status="APPROVED",
            authorized=True,
        )
        self.assertEqual(result["execution_status"], "SUCCEEDED")
        self.assertTrue(result["external_action_executed"])

    def test_executor_failure_becomes_failure_outcome(self):
        result = self.adapter.run(
            self.governance_go,
            run_id="UR-001",
            project_id="demo",
            action_key="bounded-test",
            executor=lambda: {"status": "FAILED", "error": "provider_timeout"},
        )
        self.assertEqual(result["execution_status"], "FAILED")
        self.assertEqual(result["outcome_status"], "FAILURE")
        self.assertEqual(result["error"], "provider_timeout")

    def test_executor_exception_is_captured(self):
        def fail():
            raise RuntimeError("boom")

        result = self.adapter.run(
            self.governance_go,
            run_id="UR-001",
            project_id="demo",
            action_key="bounded-test",
            executor=fail,
        )
        self.assertEqual(result["execution_status"], "FAILED")
        self.assertEqual(result["outcome_status"], "FAILURE")
        self.assertIn("RuntimeError:boom", result["error"])

    def test_non_mapping_executor_result_fails_closed(self):
        result = self.adapter.run(
            self.governance_go,
            run_id="UR-001",
            project_id="demo",
            action_key="bounded-test",
            executor=lambda: "bad",
        )
        self.assertEqual(result["execution_status"], "FAILED")
        self.assertEqual(result["outcome_status"], "FAILURE")

    def test_execution_id_is_deterministic(self):
        a = self.adapter.execution_id(
            run_id="UR-001", project_id="demo", action_key="bounded-test"
        )
        b = self.adapter.execution_id(
            run_id="UR-001", project_id="demo", action_key="bounded-test"
        )
        self.assertEqual(a, b)
        self.assertTrue(a.startswith("EXE-"))

    def test_different_action_keys_do_not_collide(self):
        a = self.adapter.execution_id(
            run_id="UR-001", project_id="demo", action_key="action-a"
        )
        b = self.adapter.execution_id(
            run_id="UR-001", project_id="demo", action_key="action-b"
        )
        self.assertNotEqual(a, b)

if __name__ == "__main__":
    unittest.main()
