import unittest

from src.execution_intent_planner import ExecutionIntentPlanner


class TestExecutionIntentPlanner(unittest.TestCase):
    def setUp(self):
        self.plan = {
            "status": "RECOMMEND",
            "project_id": "P1",
            "plan_id": "UDI-ABC123",
            "selected_route": {
                "provider": "provider_a",
                "tool": "search_a",
                "score": 1.2,
                "cost_usd": 0.01,
                "latency_ms": 100,
            },
            "decision_basis": {
                "uncertainty": "LOW",
                "reliability": "STRONG",
                "resource_pressure": "NORMAL",
                "latency_posture": "NORMAL",
                "cost_posture": "WITHIN_BUDGET",
            },
            "governance_required": True,
        }

    def build(self, **changes):
        data = dict(
            decision_plan=self.plan,
            action="read_only_inspection",
            payload={"q": "hello"},
            project_id="P1",
            run_id="R1",
            requested_by="operator",
            context={"source": "test"},
        )
        data.update(changes)
        return ExecutionIntentPlanner.build_intent(**data)

    def test_recommend_plan_creates_deterministic_intent(self):
        a = self.build()
        b = self.build()
        self.assertEqual(a["status"], "PLANNED")
        self.assertEqual(a["intent_id"], b["intent_id"])
        self.assertEqual(a["execution_request"]["idempotency_key"], b["execution_request"]["idempotency_key"])

    def test_refine_plan_is_blocked(self):
        plan = dict(self.plan, status="REFINE")
        out = self.build(decision_plan=plan)
        self.assertEqual(out["status"], "BLOCKED")
        self.assertEqual(out["reason"], "decision_plan_not_executable")

    def test_hold_plan_is_blocked(self):
        plan = dict(self.plan, status="HOLD")
        out = self.build(decision_plan=plan)
        self.assertEqual(out["reason"], "decision_plan_not_executable")

    def test_missing_selected_route_is_blocked(self):
        plan = dict(self.plan)
        plan.pop("selected_route")
        out = self.build(decision_plan=plan)
        self.assertEqual(out["reason"], "selected_route_required")

    def test_payload_must_be_object(self):
        out = self.build(payload=["not-an-object"])
        self.assertEqual(out["reason"], "payload_must_be_object")

    def test_consequential_action_requires_governed_review(self):
        out = self.build(action="publish_public_content")
        self.assertEqual(out["status"], "PLANNED")
        self.assertTrue(out["consequential_action"])
        self.assertTrue(out["governance_review_required"])

    def test_governance_cannot_be_downgraded(self):
        plan = dict(self.plan, governance_required=False)
        out = self.build(decision_plan=plan)
        self.assertEqual(out["status"], "PLANNED")
        self.assertTrue(out["consequential_action"] is False)
        self.assertFalse(out["governance_review_required"])
        self.assertEqual(out["governance_authority"], "POLICY_AND_GOVERNANCE_REMAIN_AUTHORITATIVE")

    def test_preflight_returns_ready_without_execution(self):
        out = self.build()
        pf = ExecutionIntentPlanner.preflight(out, expected_project_id="P1")
        self.assertEqual(pf["status"], "READY_FOR_GOVERNED_SUBMISSION")
        self.assertFalse(pf["external_action_executed"])

    def test_preflight_rejects_project_mismatch(self):
        out = self.build()
        pf = ExecutionIntentPlanner.preflight(out, expected_project_id="OTHER")
        self.assertEqual(pf["reason"], "project_mismatch")

    def test_preflight_rejects_tampered_idempotency(self):
        out = self.build()
        out["execution_request"]["idempotency_key"] = "tampered"
        pf = ExecutionIntentPlanner.preflight(out, expected_project_id="P1")
        self.assertEqual(pf["reason"], "idempotency_key_mismatch")

    def test_preflight_rejects_execution_after_start(self):
        out = self.build()
        out["execution_started"] = True
        pf = ExecutionIntentPlanner.preflight(out)
        self.assertEqual(pf["reason"], "intent_already_executed")

    def test_invalid_governance_authority_fails_closed(self):
        out = self.build()
        out["governance_authority"] = "DISABLED"
        pf = ExecutionIntentPlanner.preflight(out)
        self.assertEqual(pf["reason"], "governance_authority_invalid")

    def test_recovery_outcome_is_preserved(self):
        out = self.build()
        updated = ExecutionIntentPlanner.record_execution_outcome(
            out, {"status": "RECOVERY_REQUIRED", "execution": {"state": "RECOVERY_REQUIRED"}}
        )
        self.assertTrue(updated["execution_started"])
        self.assertFalse(updated["execution_completed"])
        self.assertTrue(updated["recovery_required"])

    def test_success_outcome_marks_complete(self):
        out = self.build()
        updated = ExecutionIntentPlanner.record_execution_outcome(
            out, {"status": "SUCCEEDED", "execution": {"state": "SUCCEEDED"}}
        )
        self.assertTrue(updated["execution_started"])
        self.assertTrue(updated["execution_completed"])
        self.assertFalse(updated["recovery_required"])


if __name__ == "__main__":
    unittest.main()
