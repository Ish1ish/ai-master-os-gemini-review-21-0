from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.src.project_workspace_store import ProjectWorkspaceStore
from test_patch22_persistent_project_workspace import _plan_result


class TestProjectWorkspaceLifecycleHardening(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectWorkspaceStore(Path(self.tmp.name) / "workspace.sqlite3")

    def tearDown(self):
        self.tmp.cleanup()

    def _create(self, project_id="P24-WS", owner="alice"):
        return self.store.write({
            "operation": "create_from_plan",
            "project_id": project_id,
            "requested_by": owner,
            "plan_result": _plan_result(),
        })

    def test_owner_is_checked_before_revision_conflict_can_leak_metadata(self):
        self._create(owner="alice")
        advanced = self.store.write({
            "operation": "append_note",
            "project_id": "P24-WS",
            "requested_by": "alice",
            "expected_revision": 1,
            "note": "Move workspace to revision two.",
        })
        self.assertEqual(advanced["revision"], 2)

        denied = self.store.write({
            "operation": "append_note",
            "project_id": "P24-WS",
            "requested_by": "bob",
            "expected_revision": 1,
            "note": "Try to infer another owner's current revision.",
        })

        self.assertEqual(denied["status"], "NOT_FOUND")
        self.assertEqual(denied["reason"], "project_workspace_not_found")
        self.assertNotIn("current_revision", denied)
        self.assertNotIn("expected_revision", denied)

    def test_completed_project_cannot_be_reopened_or_mutated_except_archive(self):
        created = self._create()
        revision = created["revision"]
        for task in created["workspace"]["tasks"]:
            result = self.store.write({
                "operation": "update_task",
                "project_id": "P24-WS",
                "requested_by": "alice",
                "expected_revision": revision,
                "task_id": task["task_id"],
                "task_status": "DONE",
            })
            self.assertEqual(result["status"], "UPDATED")
            revision = result["revision"]

        completed = self.store.write({
            "operation": "update_status",
            "project_id": "P24-WS",
            "requested_by": "alice",
            "expected_revision": revision,
            "project_status": "COMPLETED",
        })
        self.assertEqual(completed["workspace"]["status"], "COMPLETED")
        revision = completed["revision"]

        for operation, extra in [
            ("append_note", {"note": "A late mutation."}),
            ("record_decision", {"title": "Late decision", "rationale": "No mutation after completion."}),
            ("update_task", {"task_id": "M01-T01", "task_status": "DONE"}),
            ("update_status", {"project_status": "ACTIVE"}),
            ("update_status", {"project_status": "PAUSED"}),
            ("update_status", {"project_status": "COMPLETED"}),
        ]:
            with self.subTest(operation=operation, extra=extra):
                denied = self.store.write({
                    "operation": operation,
                    "project_id": "P24-WS",
                    "requested_by": "alice",
                    "expected_revision": revision,
                    **extra,
                })
                self.assertEqual(denied["status"], "CONFLICT")
                self.assertEqual(denied["reason"], "project_workspace_completed")

        archived = self.store.write({
            "operation": "update_status",
            "project_id": "P24-WS",
            "requested_by": "alice",
            "expected_revision": revision,
            "project_status": "ARCHIVED",
        })
        self.assertEqual(archived["status"], "UPDATED")
        self.assertEqual(archived["workspace"]["status"], "ARCHIVED")

    def test_paused_project_rejects_task_progress_but_allows_notes_and_resume(self):
        created = self._create()
        paused = self.store.write({
            "operation": "update_status",
            "project_id": "P24-WS",
            "requested_by": "alice",
            "expected_revision": created["revision"],
            "project_status": "PAUSED",
        })
        revision = paused["revision"]

        task_update = self.store.write({
            "operation": "update_task",
            "project_id": "P24-WS",
            "requested_by": "alice",
            "expected_revision": revision,
            "task_id": "M01-T01",
            "task_status": "IN_PROGRESS",
        })
        self.assertEqual(task_update["status"], "CONFLICT")
        self.assertEqual(task_update["reason"], "project_workspace_paused")

        note = self.store.write({
            "operation": "append_note",
            "project_id": "P24-WS",
            "requested_by": "alice",
            "expected_revision": revision,
            "note": "Project is paused pending operator review.",
            "note_type": "blocker",
        })
        self.assertEqual(note["status"], "UPDATED")
        revision = note["revision"]

        resumed = self.store.write({
            "operation": "update_status",
            "project_id": "P24-WS",
            "requested_by": "alice",
            "expected_revision": revision,
            "project_status": "ACTIVE",
        })
        self.assertEqual(resumed["workspace"]["status"], "ACTIVE")

        progressed = self.store.write({
            "operation": "update_task",
            "project_id": "P24-WS",
            "requested_by": "alice",
            "expected_revision": resumed["revision"],
            "task_id": "M01-T01",
            "task_status": "IN_PROGRESS",
        })
        self.assertEqual(progressed["status"], "UPDATED")
        self.assertEqual(progressed["workspace"]["task_tracking"]["in_progress_task_count"], 1)


if __name__ == "__main__":
    unittest.main()
