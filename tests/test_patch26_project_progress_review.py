from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.src.project_progress_review import project_progress_review_tool
from core.src.project_workspace_store import ProjectWorkspaceStore
from test_patch22_persistent_project_workspace import _plan_result
from unified_runtime.integrated_runtime import RealUnifiedRuntime


class TestProjectProgressReview(unittest.TestCase):
    PRINCIPAL = {
        "status": "AUTHENTICATED",
        "authenticated": True,
        "principal": "operator-26",
        "principal_id": "operator-26",
        "scopes": ["run:submit", "job:execute", "governance:evaluate"],
        "roles": ["operator"],
        "auth_method": "test",
    }

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = ProjectWorkspaceStore(self.root / "workspace.sqlite3")
        self.created = self.store.write({
            "operation": "create_from_plan",
            "project_id": "P26-REVIEW",
            "requested_by": "operator-26",
            "plan_result": _plan_result(),
        })
        self.revision = self.created["revision"]

    def tearDown(self):
        self.tmp.cleanup()

    def _update(self, task_id, status, note=""):
        result = self.store.write({
            "operation": "update_task",
            "project_id": "P26-REVIEW",
            "requested_by": "operator-26",
            "expected_revision": self.revision,
            "task_id": task_id,
            "task_status": status,
            "note": note,
        })
        self.assertEqual(result["status"], "UPDATED")
        self.revision = result["revision"]
        return result

    def test_review_groups_blocked_in_progress_and_todo_without_mutating(self):
        self._update("M01-T01", "BLOCKED", "Waiting for interview access.")
        self._update("M01-T02", "IN_PROGRESS", "Sample menu under review.")
        before = self.store.read({
            "operation": "get",
            "project_id": "P26-REVIEW",
            "requested_by": "operator-26",
        })
        event_count = len(before["events"])

        review = project_progress_review_tool({
            "project_id": "P26-REVIEW",
            "requested_by": "operator-26",
        }, store=self.store)

        self.assertEqual(review["status"], "OK")
        self.assertEqual(review["review_type"], "DETERMINISTIC_READ_ONLY")
        self.assertEqual(review["workspace_revision"], self.revision)
        self.assertEqual(review["project_status"], "ACTIVE")
        self.assertEqual(review["blocked_tasks"][0]["task_id"], "M01-T01")
        self.assertEqual(review["in_progress_tasks"][0]["task_id"], "M01-T02")
        self.assertGreaterEqual(len(review["next_todo_tasks"]), 1)
        self.assertIn("blockers", review["suggested_next_step"])
        self.assertFalse(review["workspace_mutated"])
        self.assertFalse(review["external_actions_executed"])
        self.assertFalse(review["decision_grade_evidence"])

        after = self.store.read({
            "operation": "get",
            "project_id": "P26-REVIEW",
            "requested_by": "operator-26",
        })
        self.assertEqual(after["revision"], before["revision"])
        self.assertEqual(len(after["events"]), event_count)
        self.assertEqual(after["workspace"]["tasks"], before["workspace"]["tasks"])

    def test_review_hides_workspace_from_another_owner(self):
        result = project_progress_review_tool({
            "project_id": "P26-REVIEW",
            "requested_by": "someone-else",
        }, store=self.store)
        self.assertEqual(result["status"], "NOT_FOUND")
        self.assertEqual(result["reason"], "project_workspace_not_found")
        self.assertNotIn("workspace_revision", result)
        self.assertFalse(result["workspace_mutated"])

    def test_review_requires_project_id(self):
        with self.assertRaisesRegex(
            ValueError, "project_progress_review_project_id_required"
        ):
            project_progress_review_tool({"requested_by": "operator-26"}, store=self.store)

    def test_review_suggests_no_task_mutation_for_paused_project(self):
        paused = self.store.write({
            "operation": "update_status",
            "project_id": "P26-REVIEW",
            "requested_by": "operator-26",
            "expected_revision": self.revision,
            "project_status": "PAUSED",
        })
        self.revision = paused["revision"]
        review = project_progress_review_tool({
            "project_id": "P26-REVIEW",
            "requested_by": "operator-26",
        }, store=self.store)
        self.assertEqual(review["project_status"], "PAUSED")
        self.assertIn("paused", review["suggested_next_step"])
        self.assertFalse(review["workspace_mutated"])

    def test_runtime_binds_review_to_authenticated_project(self):
        runtime = RealUnifiedRuntime(str(self.root / "runtime"))
        result = runtime._submit_governed_execution(
            execution_contract={
                "action": "read_only_inspection",
                "tool_name": "provider.project.workspace.review",
                "payload": {"project_id": "UNAUTHORIZED-PROJECT"},
            },
            decision_stage={
                "status": "RECOMMEND",
                "plan_id": "PLAN-P26",
                "selected_route": {
                    "provider": "internal",
                    "tool": "provider.project.workspace.review",
                },
            },
            evaluation={},
            evidence_payload={},
            decision_surface={},
            governance={"posture": "PROCEED_TO_EXECUTION_GATE"},
            run_id="RUN-P26",
            project_id="AUTHORIZED-PROJECT",
            principal={"principal": "operator-26"},
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["reason"], "project_workspace_project_binding_invalid"
        )

    def test_runtime_rejects_review_tool_under_mutation_action(self):
        runtime = RealUnifiedRuntime(str(self.root / "runtime-review-mismatch"))
        result = runtime._submit_governed_execution(
            execution_contract={
                "action": "update_project_workspace",
                "tool_name": "provider.project.workspace.review",
                "payload": {"project_id": "AUTHORIZED-PROJECT"},
            },
            decision_stage={
                "status": "RECOMMEND",
                "plan_id": "PLAN-P26-MISMATCH",
                "selected_route": {
                    "provider": "internal",
                    "tool": "provider.project.workspace.review",
                },
            },
            evaluation={},
            evidence_payload={},
            decision_surface={},
            governance={"posture": "PROCEED_TO_EXECUTION_GATE"},
            run_id="RUN-P26-MISMATCH",
            project_id="AUTHORIZED-PROJECT",
            principal={"principal": "operator-26"},
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["reason"], "project_workspace_action_tool_binding_invalid"
        )


if __name__ == "__main__":
    unittest.main()
