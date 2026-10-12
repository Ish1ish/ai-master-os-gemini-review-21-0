from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.src.project_workspace_store import ProjectWorkspaceStore
from test_patch22_persistent_project_workspace import _plan_result


class TestProjectWorkspaceMilestoneProgress(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectWorkspaceStore(Path(self.tmp.name) / "workspace.sqlite3")
        created = self.store.write({
            "operation": "create_from_plan",
            "project_id": "P25-MILESTONES",
            "requested_by": "operator-25",
            "plan_result": _plan_result(),
        })
        self.revision = created["revision"]

    def tearDown(self):
        self.tmp.cleanup()

    def _update_task(self, task_id, status):
        result = self.store.write({
            "operation": "update_task",
            "project_id": "P25-MILESTONES",
            "requested_by": "operator-25",
            "expected_revision": self.revision,
            "task_id": task_id,
            "task_status": status,
        })
        self.assertEqual(result["status"], "UPDATED")
        self.revision = result["revision"]
        return result

    def test_new_workspace_exposes_milestone_level_progress(self):
        result = self.store.read({
            "operation": "get",
            "project_id": "P25-MILESTONES",
            "requested_by": "operator-25",
        })
        tracking = result["workspace"]["milestone_tracking"]
        self.assertEqual(tracking["milestone_count"], 2)
        self.assertEqual(tracking["completed_milestone_count"], 0)
        self.assertEqual(tracking["blocked_milestone_count"], 0)
        self.assertEqual(tracking["progress_percent"], 0)
        self.assertEqual(tracking["milestones"][0]["milestone_id"], "M01")
        self.assertEqual(tracking["milestones"][0]["status"], "TODO")
        self.assertEqual(tracking["milestones"][0]["task_tracking"]["task_count"], 2)
        self.assertEqual(tracking["milestones"][1]["milestone_id"], "M02")
        self.assertEqual(tracking["milestones"][1]["task_tracking"]["task_count"], 1)
        self.assertEqual(
            tracking["milestones"][0]["completion_criteria"],
            "Interview notes and pilot interest are recorded.",
        )

    def test_milestone_status_tracks_done_in_progress_and_blocked_tasks(self):
        self._update_task("M01-T01", "DONE")
        partial = self._update_task("M01-T02", "IN_PROGRESS")
        first = partial["workspace"]["milestone_tracking"]["milestones"][0]
        self.assertEqual(first["status"], "IN_PROGRESS")
        self.assertEqual(first["task_tracking"]["progress_percent"], 50)

        blocked = self._update_task("M02-T01", "BLOCKED")
        tracking = blocked["workspace"]["milestone_tracking"]
        self.assertEqual(tracking["blocked_milestone_count"], 1)
        second = tracking["milestones"][1]
        self.assertEqual(second["status"], "BLOCKED")
        self.assertEqual(second["task_tracking"]["blocked_task_count"], 1)
        # Next-action tasks are tracked project-wide but do not inflate milestone counts.
        self.assertEqual(tracking["milestones"][0]["task_tracking"]["task_count"], 2)
        self.assertEqual(tracking["milestones"][1]["task_tracking"]["task_count"], 1)

    def test_completed_tasks_mark_milestone_done_and_list_includes_summary(self):
        self._update_task("M01-T01", "DONE")
        done = self._update_task("M01-T02", "SKIPPED")
        tracking = done["workspace"]["milestone_tracking"]
        self.assertEqual(tracking["completed_milestone_count"], 1)
        self.assertEqual(tracking["milestones"][0]["status"], "DONE")
        self.assertEqual(tracking["milestones"][0]["task_tracking"]["progress_percent"], 100)

        listed = self.store.read({
            "operation": "list",
            "requested_by": "operator-25",
            "limit": 10,
        })
        self.assertEqual(listed["count"], 1)
        summary = listed["projects"][0]["milestone_tracking"]
        self.assertEqual(summary["milestone_count"], 2)
        self.assertEqual(summary["completed_milestone_count"], 1)
        self.assertEqual(summary["milestones"][0]["status"], "DONE")

    def test_milestone_progress_is_derived_not_saved_as_stale_state(self):
        self._update_task("M01-T01", "DONE")
        reopened = ProjectWorkspaceStore(self.store.db_path).read({
            "operation": "get",
            "project_id": "P25-MILESTONES",
            "requested_by": "operator-25",
        })
        self.assertEqual(reopened["workspace"]["milestone_tracking"]["progress_percent"], 25)
        # Only one of the four project tasks is completed. Milestone-level
        # status is derived from the underlying task records on each read.
        self.assertEqual(
            reopened["workspace"]["milestone_tracking"]["milestones"][0]["status"],
            "IN_PROGRESS",
        )


if __name__ == "__main__":
    unittest.main()
