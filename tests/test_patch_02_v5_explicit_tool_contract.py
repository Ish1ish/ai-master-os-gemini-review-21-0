import unittest

from core.src.execution_intent_planner import ExecutionIntentPlanner


class TestPatch02V5ExplicitToolContract(unittest.TestCase):
    def setUp(self):
        self.plan = {
            "status": "RECOMMEND",
            "project_id": "P-V5",
            "plan_id": "UDI-V5",
            "selected_route": {
                "provider": "unified-runtime",
                "tool": "decision-intelligence",
                "score": 1.0,
            },
            "decision_basis": {"uncertainty": "LOW", "reliability": "STRONG"},
            "governance_required": True,
        }

    def test_explicit_tool_overrides_advisory_route_tool(self):
        out = ExecutionIntentPlanner.build_intent(
            decision_plan=self.plan,
            action="read_only_inspection",
            tool_name="internal.echo",
            payload={"value": "v5"},
            project_id="P-V5",
            run_id="R-V5",
            requested_by="operator-01",
            context={
                "confidence": "high",
                "evidence_refs": ["EV-V5"],
                "evidence_boundary": "local_evidence_supported",
            },
        )
        self.assertEqual(out["status"], "PLANNED")
        self.assertEqual(out["tool_name"], "internal.echo")
        self.assertEqual(out["execution_request"]["tool_name"], "internal.echo")
        self.assertEqual(out["decision_plan_id"], self.plan["plan_id"])

    def test_legacy_call_without_explicit_tool_preserves_route_tool(self):
        out = ExecutionIntentPlanner.build_intent(
            decision_plan=self.plan,
            action="read_only_inspection",
            payload={"value": "legacy"},
            project_id="P-V5",
            run_id="R-V5-LEGACY",
            requested_by="operator-01",
            context={},
        )
        self.assertEqual(out["status"], "PLANNED")
        self.assertEqual(out["tool_name"], "decision-intelligence")


if __name__ == "__main__":
    unittest.main()
