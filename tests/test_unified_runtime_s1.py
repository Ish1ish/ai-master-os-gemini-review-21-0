import unittest

from unified_runtime.s1 import S1Input, build_s1_runtime


class TestS1(unittest.TestCase):
    def test_deterministic_run_and_trace_ids(self):
        req = S1Input(project_id="demo", intent="validate demand")
        a = build_s1_runtime()(req)
        b = build_s1_runtime()(req)
        self.assertEqual(a.run_id, b.run_id)
        self.assertEqual(a.trace_id, b.trace_id)

    def test_empty_intent_fails_closed(self):
        req = S1Input(project_id="demo", intent=" ")
        result = build_s1_runtime()(req)
        self.assertTrue(result.terminal)
        self.assertEqual(result.stages["INTENT"].status, "BLOCKED")
        self.assertEqual(result.next_stage, "INTENT")

    def test_s1_reaches_decision_without_external_action(self):
        req = S1Input(
            project_id="demo",
            intent="choose the next validation step",
            goal="reduce uncertainty",
            requested_language="ar",
        )
        result = build_s1_runtime()(req)
        self.assertFalse(result.terminal)
        self.assertEqual(result.next_stage, "EVIDENCE")
        self.assertEqual(
            list(result.stages.keys()),
            ["INTENT", "UNDERSTAND", "ROUTE", "DECISION"],
        )
        self.assertFalse(result.stages["ROUTE"].data["external_action"])
        self.assertFalse(result.stages["DECISION"].data["external_action"])

    def test_understand_adapter_is_used(self):
        seen = {}

        def understand(req):
            seen["intent"] = req.intent
            return {"normalized_goal": "test", "problem_statement": "p"}

        result = build_s1_runtime(understand=understand)(
            S1Input(project_id="demo", intent="abc")
        )
        self.assertEqual(seen["intent"], "abc")
        self.assertEqual(
            result.stages["UNDERSTAND"].data["normalized_goal"], "test"
        )

    def test_route_adapter_fail_closed(self):
        def bad_route(req, understood):
            return {}

        result = build_s1_runtime(route=bad_route)(
            S1Input(project_id="demo", intent="abc")
        )
        self.assertTrue(result.terminal)
        self.assertEqual(result.next_stage, "ROUTE")
        self.assertEqual(result.stages["ROUTE"].status, "BLOCKED")

    def test_decision_adapter_isolation(self):
        def decision(req, understood, routed):
            return {
                "status": "READY",
                "recommendation": "run a bounded experiment",
                "external_action": False,
            }

        result = build_s1_runtime(decision=decision)(
            S1Input(project_id="demo", intent="abc")
        )
        self.assertEqual(result.stages["DECISION"].data["status"], "READY")
        self.assertFalse(result.stages["DECISION"].data["external_action"])

if __name__ == "__main__":
    unittest.main()
