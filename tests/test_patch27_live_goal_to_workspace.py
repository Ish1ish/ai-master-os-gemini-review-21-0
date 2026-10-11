from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.src.goal_to_project_workspace import real_goal_to_project_workspace
from core.src.live_providers import provider_configuration_status
from core.src.project_workspace_store import ProjectWorkspaceStore
from unified_runtime.integrated_runtime import RealUnifiedRuntime


PRINCIPAL = {
    "status": "AUTHENTICATED",
    "authenticated": True,
    "principal": "operator-27",
    "principal_id": "operator-27",
    "scopes": ["run:submit", "job:execute", "governance:evaluate"],
    "roles": ["operator"],
    "auth_method": "patch27-integration-test",
}

PROJECT_ID = "PATCH27-GOAL-WORKSPACE"
GOAL = "Assess demand for affordable meal preparation for office workers in Cairo"
AUDIENCE = "office workers"
CONSTRAINTS = {
    "location": "Cairo, Egypt",
    "budget": {"amount": "10000", "currency": "EGP"},
}

_SYNTHESIS_OUTPUT = {
    "executive_summary": "The returned snippet is an initial signal only.",
    "evidence_findings": [{
        "claim": "The supplied search snippet discusses prepared-meal services.",
        "source_ids": ["S001"],
        "confidence": "low",
    }],
    "hypotheses": [{
        "hypothesis": "Some office workers may value an affordable meal-prep option.",
        "reasoning": "The supplied snippet alone does not establish demand or willingness to pay.",
        "validation_step": "Interview target customers and test a small paid pre-order offer.",
        "source_ids": ["S001"],
    }],
    "recommendations": [{
        "recommendation": "Validate interest before committing significant capital.",
        "basis_source_ids": ["S001"],
        "assumptions": ["A small pilot can be organized without major fixed costs."],
        "validation_step": "Record interview results and paid pre-order conversion.",
    }],
    "risks": [{
        "risk": "Search snippets may omit important context.",
        "mitigation": "Inspect the full source page and seek independent corroboration.",
        "source_ids": [],
    }],
    "evidence_gaps": ["Only the supplied search-result snippet has been reviewed."],
}

_PLAN_OUTPUT = {
    "project_title": "Affordable Meal Prep Demand Pilot",
    "executive_summary": "Validate demand through customer discovery before scaling.",
    "recommended_approach": "Start with a narrow audience and a small validation pilot.",
    "minimum_viable_launch": "Interview target customers and offer a limited pre-order test.",
    "assumptions": [{
        "assumption": "Target customers can be reached for interviews.",
        "why_it_matters": "Without access, customer discovery will be delayed.",
        "validation_method": "Recruit a small set of office workers and track responses.",
        "source_ids": [],
    }],
    "milestones": [{
        "name": "Demand validation",
        "objective": "Gather first-hand evidence of customer needs and willingness to pay.",
        "duration_days": 7,
        "tasks": ["Interview ten target customers", "Document price expectations"],
        "completion_criteria": "Interview findings and follow-up decisions are recorded.",
    }, {
        "name": "Small pilot",
        "objective": "Test a limited offer before considering expansion.",
        "duration_days": 14,
        "tasks": ["Prepare a limited pre-order offer"],
        "completion_criteria": "Pilot outcomes and costs are documented.",
    }],
    "budget_items": [{
        "category": "Pilot ingredients",
        "amount_min": 500,
        "amount_max": 1000,
        "basis": "planning_estimate",
        "source_ids": [],
        "assumptions": ["Small initial quantity only."],
        "notes": "Illustrative planning range; not a supplier quote.",
    }],
    "success_metrics": [{
        "metric": "Completed target-customer interviews",
        "target": "10 interviews",
        "measurement": "Count documented interviews",
        "review_interval": "At the end of week one",
    }],
    "risks": [{
        "risk": "Interest may not convert into paid orders.",
        "likelihood": "medium",
        "mitigation": "Use a limited paid pre-order test before expanding.",
        "source_ids": ["S001"],
    }],
    "next_actions": [{
        "action": "Recruit ten target customers for interviews",
        "priority": "high",
        "due_in_days": 3,
        "success_criteria": "Ten interview notes are recorded",
    }],
    "open_questions": ["Which local food-safety and business requirements apply?"],
}


def _model_response(value):
    return {"text": json.dumps(value, ensure_ascii=False)}


class TestGovernedGoalToWorkspaceIntegration(unittest.TestCase):
    """Fast end-to-end across runtime/provider adapters with provider replies mocked."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = ProjectWorkspaceStore(self.root / "project_workspace.sqlite3")
        self.runtime = RealUnifiedRuntime(str(self.root / "runtime"))
        self.runtime.register_execution_tool(
            "provider.project.goal-to-workspace",
            lambda payload: real_goal_to_project_workspace(payload, store=self.store),
            version="1.0.0",
            retry_safe=False,
        )

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def _submit(self, run_suffix: str):
        return self.runtime.run(
            run_id="PATCH27-RUN-" + run_suffix,
            project_id=PROJECT_ID,
            strategy_id="PATCH27-STRATEGY-" + run_suffix,
            intent="Research the market, build an internal plan, and save the project",
            goal=GOAL,
            audience=AUDIENCE,
            constraints=CONSTRAINTS,
            requested_language="en",
            principal=PRINCIPAL,
            execution_contract={
                "action": "update_project_workspace",
                "tool_name": "provider.project.goal-to-workspace",
                "payload": {
                    "project_id": PROJECT_ID,
                    "goal": GOAL,
                    "audience": AUDIENCE,
                    "constraints": CONSTRAINTS,
                    "requested_language": "en",
                    "max_queries": 1,
                },
            },
        )

    @patch("core.src.project_plan_generator.model_provider")
    @patch("core.src.research_synthesis.model_provider")
    @patch("core.src.canonical_provider_tools.search_provider")
    def test_governed_submission_then_explicit_drive_reaches_persistent_workspace(
        self, search, synthesis_model, plan_model
    ):
        search.return_value = {
            "results": [{
                "url": "https://example.com/market",
                "title": "Prepared meal services overview",
                "snippet": "A search-result snippet describing prepared meal services.",
            }]
        }
        synthesis_model.return_value = _model_response(_SYNTHESIS_OUTPUT)
        plan_model.return_value = _model_response(_PLAN_OUTPUT)

        submitted = self._submit("MOCKED")
        governed = submitted.get("governed_execution") or {}
        self.assertEqual(governed.get("status"), "READY")
        # Submission creates a governed intent only: no provider/persistence call yet.
        search.assert_not_called()
        synthesis_model.assert_not_called()
        plan_model.assert_not_called()
        before = self.store.read({
            "operation": "get",
            "project_id": PROJECT_ID,
            "requested_by": PRINCIPAL["principal"],
        })
        self.assertEqual(before["status"], "NOT_FOUND")

        driven = self.runtime.execute_governed_intent(
            governed["intent"]["intent_id"], principal=PRINCIPAL
        )
        self.assertEqual(driven.get("status"), "SUCCEEDED")
        search.assert_called_once()
        synthesis_model.assert_called_once()
        plan_model.assert_called_once()

        saved = self.store.read({
            "operation": "get",
            "project_id": PROJECT_ID,
            "requested_by": PRINCIPAL["principal"],
        })
        self.assertEqual(saved["status"], "OK")
        workspace = saved["workspace"]
        self.assertEqual(workspace["owner_id"], PRINCIPAL["principal"])
        self.assertEqual(workspace["project_id"], PROJECT_ID)
        self.assertEqual(workspace["status"], "ACTIVE")
        self.assertEqual(workspace["sources"][0]["source_id"], "S001")
        self.assertEqual(workspace["sources"][0]["url"], "https://example.com/market")
        self.assertEqual(workspace["research_status"], "COMPLETE")
        self.assertEqual(workspace["task_tracking"]["task_count"], 4)
        self.assertFalse(workspace["decision_grade_evidence"])
        self.assertFalse(workspace["external_actions_executed"])

    @unittest.skipUnless(
        os.getenv("AI_OS_RUN_LIVE_GOAL_TO_WORKSPACE_TEST") == "1",
        "opt-in only: set AI_OS_RUN_LIVE_GOAL_TO_WORKSPACE_TEST=1 to make live provider calls",
    )
    def test_live_provider_goal_to_workspace_pipeline(self):
        """Opt-in real-provider check: one research query, one synthesis call, one plan call."""
        config = provider_configuration_status()
        if config["status"] != "CONFIGURED":
            self.skipTest(
                "live provider configuration missing: " + ", ".join(config["missing"])
            )

        submitted = self._submit("LIVE")
        governed = submitted.get("governed_execution") or {}
        self.assertEqual(
            governed.get("status"), "READY",
            msg="governed submission did not become READY: " + repr(governed),
        )

        # Provider requests happen only at this explicit execution drive.
        driven = self.runtime.execute_governed_intent(
            governed["intent"]["intent_id"], principal=PRINCIPAL
        )
        self.assertEqual(
            driven.get("status"), "SUCCEEDED",
            msg="live governed execution did not succeed: " + repr(driven),
        )

        saved = self.store.read({
            "operation": "get",
            "project_id": PROJECT_ID,
            "requested_by": PRINCIPAL["principal"],
        })
        self.assertEqual(saved["status"], "OK")
        workspace = saved["workspace"]
        self.assertEqual(workspace["owner_id"], PRINCIPAL["principal"])
        self.assertEqual(workspace["status"], "ACTIVE")
        self.assertGreaterEqual(len(workspace["sources"]), 1)
        self.assertGreaterEqual(workspace["task_tracking"]["task_count"], 1)
        self.assertIn(workspace["research_status"], {"COMPLETE", "PARTIAL"})
        self.assertFalse(workspace["decision_grade_evidence"])
        self.assertFalse(workspace["external_actions_executed"])
        self.assertEqual(saved["revision"], 1)


if __name__ == "__main__":
    unittest.main()
