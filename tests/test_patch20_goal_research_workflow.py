from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch

from core.src.goal_research_workflow import real_goal_research_workflow
from unified_runtime.integrated_runtime import RealUnifiedRuntime


class TestGoalResearchWorkflow(unittest.TestCase):
    def setUp(self):
        self.research_result = {
            "provider": "live_search",
            "status": "COMPLETE",
            "goal": "Validate demand for affordable prepared meals",
            "audience": "office workers",
            "queries": ["demand for prepared meals", "competitors and pricing"],
            "query_count": 2,
            "query_statuses": [
                {"query": "demand for prepared meals", "status": "SUCCEEDED", "source_count": 1},
                {"query": "competitors and pricing", "status": "SUCCEEDED", "source_count": 1},
            ],
            "result_count": 1,
            "results": [{
                "url": "https://example.com/market",
                "title": "Market overview",
                "snippet": "Example result snippet.",
                "matched_queries": ["demand for prepared meals"],
            }],
        }
        self.synthesis_result = {
            "provider": "live_model",
            "status": "COMPLETE",
            "source_count": 1,
            "sources": [{"source_id": "S001", "url": "https://example.com/market"}],
            "synthesis": {
                "executive_summary": "An initial signal needs further validation.",
                "evidence_findings": [{
                    "claim": "The page discusses the category.",
                    "source_ids": ["S001"],
                    "confidence": "low",
                }],
                "hypotheses": [],
                "recommendations": [],
                "risks": [],
                "evidence_gaps": ["Full page has not been inspected."],
            },
            "evidence_boundary": "SYNTHESIS_OF_SUPPLIED_SEARCH_SNIPPETS_NOT_FULL_PAGE_VERIFICATION",
            "decision_grade_evidence": False,
        }

    @patch("core.src.goal_research_workflow.real_research_synthesis_tool")
    @patch("core.src.goal_research_workflow.real_research_tool")
    def test_goal_runs_research_then_synthesis_and_preserves_source_map(self, research, synthesis):
        research.return_value = dict(self.research_result)
        synthesis.return_value = dict(self.synthesis_result)
        result = real_goal_research_workflow({
            "goal": "Validate demand for affordable prepared meals",
            "audience": "office workers",
            "constraints": {"location": "Cairo", "budget": "10000 EGP"},
            "requested_language": "ar",
            "max_queries": 2,
        })
        self.assertEqual(result["status"], "COMPLETE")
        self.assertFalse(result["decision_grade_evidence"])
        self.assertEqual(result["research"]["query_count"], 2)
        self.assertEqual(result["sources"][0]["source_id"], "S001")
        self.assertEqual(result["sources"][0]["url"], "https://example.com/market")
        self.assertEqual(result["workflow_stages"][0]["stage"], "live_market_research")
        self.assertEqual(result["workflow_stages"][1]["stage"], "source_grounded_synthesis")
        research.assert_called_once_with({
            "goal": "Validate demand for affordable prepared meals",
            "audience": "office workers",
            "constraints": {"location": "Cairo", "budget": "10000 EGP"},
            "max_queries": 2,
        })
        synthesis.assert_called_once_with({
            "goal": "Validate demand for affordable prepared meals",
            "audience": "office workers",
            "requested_language": "ar",
            "results": self.research_result["results"],
        })

    @patch("core.src.goal_research_workflow.real_research_synthesis_tool")
    @patch("core.src.goal_research_workflow.real_research_tool")
    def test_partial_research_status_is_preserved_in_combined_output(self, research, synthesis):
        research.return_value = {**self.research_result, "status": "PARTIAL"}
        synthesis.return_value = dict(self.synthesis_result)
        result = real_goal_research_workflow({"goal": "Validate prepared meal demand"})
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["workflow_stages"][0]["status"], "PARTIAL")
        self.assertEqual(result["workflow_stages"][1]["status"], "COMPLETE")

    @patch("core.src.goal_research_workflow.real_research_synthesis_tool")
    @patch("core.src.goal_research_workflow.real_research_tool")
    def test_synthesis_receives_only_results_from_research_stage(self, research, synthesis):
        research.return_value = dict(self.research_result)
        synthesis.return_value = dict(self.synthesis_result)
        real_goal_research_workflow({"goal": "Validate prepared meal demand"})
        kwargs = synthesis.call_args.args[0]
        self.assertEqual(kwargs["results"], self.research_result["results"])
        self.assertNotIn("constraints", kwargs)

    def test_invalid_payload_and_constraints_are_rejected(self):
        with self.assertRaisesRegex(TypeError, "goal_research_payload_must_be_mapping"):
            real_goal_research_workflow("not-a-mapping")
        with self.assertRaisesRegex(ValueError, "constraints_must_be_mapping"):
            real_goal_research_workflow({"goal": "Validate demand", "constraints": "not-a-mapping"})

    def test_missing_goal_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "goal_required"):
            real_goal_research_workflow({"goal": "  "})


class TestGovernedGoalResearchWorkflow(unittest.TestCase):
    PRINCIPAL = {
        "status": "AUTHENTICATED",
        "authenticated": True,
        "principal": "operator-01",
        "principal_id": "operator-01",
        "scopes": ["run:submit", "job:execute", "governance:evaluate"],
        "roles": ["operator"],
        "auth_method": "test",
    }

    def test_composite_tool_is_not_called_until_explicit_governed_drive(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = RealUnifiedRuntime(directory)
            calls = []

            def fake_workflow(payload):
                calls.append(dict(payload))
                return {
                    "status": "COMPLETE",
                    "result_count": 1,
                    "decision_grade_evidence": False,
                }

            runtime.register_execution_tool(
                "provider.research.workflow",
                fake_workflow,
                version="1.0.0",
                retry_safe=False,
            )
            try:
                submitted = runtime.run(
                    run_id="PATCH20-GRW-R1",
                    project_id="PATCH20-GRW-P1",
                    strategy_id="PATCH20-GRW-S1",
                    intent="Research a goal and synthesize source-grounded findings",
                    goal="Validate demand for affordable prepared meals",
                    audience="office workers",
                    principal=self.PRINCIPAL,
                    execution_contract={
                        "action": "read_only_market_research",
                        "tool_name": "provider.research.workflow",
                        "payload": {
                            "goal": "Validate demand for affordable prepared meals",
                            "audience": "office workers",
                            "constraints": {"location": "Cairo", "budget": "10000 EGP"},
                            "requested_language": "ar",
                            "max_queries": 2,
                        },
                    },
                )
                self.assertEqual(submitted["status"], "PASS")
                governed = submitted["governed_execution"]
                self.assertEqual(governed["status"], "READY")
                self.assertEqual(calls, [])
                executed = runtime.execute_governed_intent(
                    governed["intent"]["intent_id"],
                    principal=self.PRINCIPAL,
                )
                self.assertEqual(executed["status"], "SUCCEEDED")
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0]["max_queries"], 2)
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
