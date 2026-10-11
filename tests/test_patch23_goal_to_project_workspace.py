from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.src.goal_to_project_workspace import real_goal_to_project_workspace
from core.src.project_workspace_store import ProjectWorkspaceStore
from unified_runtime.integrated_runtime import RealUnifiedRuntime


def _research_result(status: str = "COMPLETE"):
    return {
        "provider": "live_goal_research_workflow",
        "status": status,
        "goal": "Validate an affordable meal-prep pilot",
        "audience": "office workers",
        "workflow_stages": [
            {"stage": "live_market_research", "status": status, "source_count": 1},
            {"stage": "source_grounded_synthesis", "status": "COMPLETE", "source_count": 1},
        ],
        "research": {"queries": ["meal-prep demand"], "query_count": 1},
        "sources": [{
            "source_id": "S001",
            "url": "https://example.com/market",
            "title": "Market overview",
            "domain": "example.com",
            "matched_queries": ["meal-prep demand"],
        }],
        "synthesis": {
            "executive_summary": "The available snippet is a preliminary signal.",
            "evidence_findings": [{
                "claim": "The page discusses the category.",
                "source_ids": ["S001"],
                "confidence": "low",
            }],
            "hypotheses": [],
            "recommendations": [],
            "risks": [],
            "evidence_gaps": ["Full-page evidence has not been reviewed."],
        },
        "evidence_boundary": "SYNTHESIS_OF_SUPPLIED_SEARCH_SNIPPETS_NOT_FULL_PAGE_VERIFICATION",
        "decision_grade_evidence": False,
    }


def _plan_result(status: str = "COMPLETE"):
    return {
        "provider": "live_model",
        "status": status,
        "generation_status": "COMPLETE",
        "plan_type": "INTERNAL_DRAFT",
        "project_goal": "Validate an affordable meal-prep pilot",
        "audience": "office workers",
        "requested_language": "en",
        "research_status": status,
        "user_budget": "10000 EGP",
        "budget_currency": "EGP",
        "budget_note": "Planning estimate only.",
        "decision_grade_evidence": False,
        "external_actions_executed": False,
        "evidence_boundary": "DRAFT_PLAN_BASED_ON_UNVERIFIED_SEARCH_SNIPPETS",
        "sources": [{
            "source_id": "S001",
            "url": "https://example.com/market",
            "title": "Market overview",
            "domain": "example.com",
            "matched_queries": ["meal-prep demand"],
        }],
        "plan": {
            "project_title": "Affordable Meal Prep Pilot",
            "executive_summary": "Validate demand before committing significant capital.",
            "recommended_approach": "Start with customer interviews and a small pilot.",
            "minimum_viable_launch": "Offer a small pre-order menu.",
            "assumptions": [],
            "milestones": [{
                "name": "Demand validation",
                "objective": "Validate problem and interest.",
                "duration_days": 7,
                "tasks": ["Interview target customers"],
                "completion_criteria": "Interview findings are recorded.",
            }],
            "budget_items": [],
            "success_metrics": [{
                "metric": "Qualified customer interviews",
                "target": "10 interviews",
                "measurement": "Completed interview notes",
                "review_interval": "At the end of week one",
            }],
            "risks": [{
                "risk": "Customers may not pay.",
                "likelihood": "medium",
                "mitigation": "Validate with paid pre-orders.",
                "source_ids": ["S001"],
            }],
            "next_actions": [{
                "action": "Interview ten target customers",
                "priority": "high",
                "due_in_days": 3,
                "success_criteria": "Record common needs and willingness to pay",
            }],
            "open_questions": ["Which local requirements apply?"],
        },
    }


class TestGoalToProjectWorkspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectWorkspaceStore(Path(self.tmp.name) / "workspace.sqlite3")
        self.payload = {
            "project_id": "P23-MEAL-PREP",
            "goal": "Validate an affordable meal-prep pilot",
            "audience": "office workers",
            "constraints": {"location": "Cairo", "budget": {"amount": "10000", "currency": "EGP"}},
            "requested_language": "en",
            "max_queries": 2,
            "requested_by": "operator-01",
        }

    def tearDown(self):
        self.tmp.cleanup()

    @patch("core.src.goal_to_project_workspace.real_project_plan_tool")
    @patch("core.src.goal_to_project_workspace.real_goal_research_workflow")
    def test_runs_research_plan_then_persists_owner_scoped_workspace(self, research, plan):
        research.return_value = _research_result()
        plan.return_value = _plan_result()

        result = real_goal_to_project_workspace(self.payload, store=self.store)

        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["workspace_save_status"], "CREATED")
        self.assertEqual(result["workspace_revision"], 1)
        self.assertEqual(result["workspace"]["owner_id"], "operator-01")
        self.assertFalse(result["decision_grade_evidence"])
        self.assertFalse(result["external_actions_executed"])
        self.assertEqual(result["workspace"]["sources"][0]["source_id"], "S001")
        self.assertEqual(result["workspace"]["task_tracking"]["task_count"], 2)
        self.assertEqual(result["workflow_stages"][-1]["stage"], "persistent_workspace")

        research.assert_called_once_with({
            "goal": self.payload["goal"],
            "audience": "office workers",
            "constraints": self.payload["constraints"],
            "requested_language": "en",
            "max_queries": 2,
        })
        plan.assert_called_once()
        plan_payload = plan.call_args.args[0]
        self.assertEqual(plan_payload["goal"], self.payload["goal"])
        self.assertEqual(plan_payload["research"]["sources"][0]["source_id"], "S001")

        reopened = ProjectWorkspaceStore(self.store.db_path).read({
            "operation": "get",
            "project_id": "P23-MEAL-PREP",
            "requested_by": "operator-01",
        })
        self.assertEqual(reopened["status"], "OK")
        self.assertEqual(reopened["workspace"]["goal"], self.payload["goal"])

    @patch("core.src.goal_to_project_workspace.real_project_plan_tool")
    @patch("core.src.goal_to_project_workspace.real_goal_research_workflow")
    def test_partial_research_remains_partial_after_workspace_save(self, research, plan):
        research.return_value = _research_result("PARTIAL")
        plan.return_value = _plan_result("PARTIAL")

        result = real_goal_to_project_workspace(self.payload, store=self.store)

        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["workspace_save_status"], "CREATED")
        self.assertEqual(result["workspace"]["research_status"], "PARTIAL")
        self.assertFalse(result["decision_grade_evidence"])

    @patch("core.src.goal_to_project_workspace.real_project_plan_tool")
    @patch("core.src.goal_to_project_workspace.real_goal_research_workflow")
    def test_partial_synthesis_stage_downgrades_pipeline_status(self, research, plan):
        mixed_research = _research_result("COMPLETE")
        mixed_research["workflow_stages"][1]["status"] = "PARTIAL"
        research.return_value = mixed_research
        plan.return_value = _plan_result("PARTIAL")

        result = real_goal_to_project_workspace(self.payload, store=self.store)

        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["workspace"]["research_status"], "PARTIAL")
        self.assertEqual(plan.call_args.args[0]["research"]["status"], "PARTIAL")

    @patch("core.src.goal_to_project_workspace.real_project_plan_tool")
    @patch("core.src.goal_to_project_workspace.real_goal_research_workflow")
    def test_project_id_is_required_before_provider_calls(self, research, plan):
        payload = dict(self.payload)
        payload.pop("project_id")
        with self.assertRaisesRegex(ValueError, "goal_to_workspace_required:project_id"):
            real_goal_to_project_workspace(payload, store=self.store)
        research.assert_not_called()
        plan.assert_not_called()

    @patch("core.src.goal_to_project_workspace.real_project_plan_tool")
    @patch("core.src.goal_to_project_workspace.real_goal_research_workflow")
    def test_non_string_project_id_is_rejected_as_invalid(self, research, plan):
        payload = dict(self.payload)
        payload["project_id"] = 123
        with self.assertRaisesRegex(ValueError, "goal_to_workspace_invalid:project_id"):
            real_goal_to_project_workspace(payload, store=self.store)
        research.assert_not_called()
        plan.assert_not_called()

    @patch("core.src.goal_to_project_workspace.real_project_plan_tool")
    @patch("core.src.goal_to_project_workspace.real_goal_research_workflow")
    def test_invalid_plan_boundary_is_rejected_before_persistence(self, research, plan):
        research.return_value = _research_result()
        invalid_plan = _plan_result()
        invalid_plan["decision_grade_evidence"] = True
        plan.return_value = invalid_plan

        with self.assertRaisesRegex(ValueError, "goal_to_workspace_plan_boundary_invalid"):
            real_goal_to_project_workspace(self.payload, store=self.store)
        self.assertEqual(self.store.read({"operation": "list"})["count"], 0)

    def test_composite_tool_is_bound_to_authenticated_runtime_project(self):
        runtime = RealUnifiedRuntime(str(Path(self.tmp.name) / "runtime"))
        result = runtime._submit_governed_execution(
            execution_contract={
                "action": "update_project_workspace",
                "tool_name": "provider.project.goal-to-workspace",
                "payload": {"project_id": "ATTACKER-CHOSEN-PROJECT", "goal": "test"},
            },
            decision_stage={
                "status": "RECOMMEND",
                "plan_id": "PLAN-P23",
                "selected_route": {
                    "provider": "live",
                    "tool": "provider.project.goal-to-workspace",
                },
            },
            evaluation={},
            evidence_payload={},
            decision_surface={},
            governance={"posture": "PROCEED_TO_EXECUTION_GATE"},
            run_id="RUN-P23",
            project_id="RUNTIME-BOUND-PROJECT",
            principal={"principal": "operator-01"},
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], "project_workspace_project_binding_invalid")

    @patch("core.src.goal_to_project_workspace.real_project_plan_tool")
    @patch("core.src.goal_to_project_workspace.real_goal_research_workflow")
    def test_existing_project_conflict_does_not_overwrite_workspace(self, research, plan):
        research.return_value = _research_result()
        plan.return_value = _plan_result()
        first = real_goal_to_project_workspace(self.payload, store=self.store)
        changed_plan = _plan_result()
        changed_plan["plan"]["executive_summary"] = "A distinct plan."
        plan.return_value = changed_plan

        result = real_goal_to_project_workspace(self.payload, store=self.store)

        self.assertEqual(first["workspace_save_status"], "CREATED")
        self.assertEqual(result["status"], "CONFLICT")
        self.assertEqual(result["workspace_save_status"], "CONFLICT")
        saved = self.store.read({
            "operation": "get",
            "project_id": "P23-MEAL-PREP",
            "requested_by": "operator-01",
        })
        self.assertEqual(
            saved["workspace"]["plan"]["executive_summary"],
            "Validate demand before committing significant capital.",
        )


if __name__ == "__main__":
    unittest.main()
