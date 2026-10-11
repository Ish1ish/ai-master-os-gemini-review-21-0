from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.src.project_workspace_store import ProjectWorkspaceStore, project_workspace_read_tool, project_workspace_write_tool
from unified_runtime.integrated_runtime import RealUnifiedRuntime


def _plan_result():
    return {
        "status": "COMPLETE",
        "generation_status": "COMPLETE",
        "plan_type": "INTERNAL_DRAFT",
        "project_goal": "Validate affordable meal-prep demand",
        "audience": "busy office workers",
        "user_budget": "10000 EGP",
        "budget_currency": "EGP",
        "budget_note": "Budget amounts are planning estimates.",
        "decision_grade_evidence": False,
        "evidence_boundary": "DRAFT_PLAN_BASED_ON_UNVERIFIED_SEARCH_SNIPPETS",
        "sources": [{
            "source_id": "S001",
            "url": "https://example.com/market",
            "title": "Market overview",
            "domain": "example.com",
            "matched_queries": ["meal prep demand"],
        }],
        "plan": {
            "project_title": "Affordable Meal Prep Pilot",
            "executive_summary": "Validate demand with a limited paid pilot.",
            "recommended_approach": "Start small and measure customer behavior.",
            "minimum_viable_launch": "Offer a small pre-order menu.",
            "assumptions": [],
            "milestones": [{
                "name": "Demand validation",
                "duration_days": 7,
                "tasks": ["Interview target customers", "Test a sample menu"],
                "objective": "Validate customer problem and interest",
                "completion_criteria": "Interview notes and pilot interest are recorded.",
            }, {
                "name": "Pilot",
                "duration_days": 14,
                "tasks": ["Accept paid pre-orders"],
                "objective": "Test execution and margin",
                "completion_criteria": "Pilot orders are fulfilled and costs recorded.",
            }],
            "budget_items": [{
                "category": "Ingredients",
                "amount_min": 1000,
                "amount_max": 1500,
                "currency": "EGP",
                "basis": "planning_estimate",
                "source_ids": [],
                "assumptions": ["Small pilot quantity"],
                "notes": "Not a quote.",
            }],
            "success_metrics": [],
            "risks": [{
                "risk": "Customers may not pay",
                "likelihood": "medium",
                "mitigation": "Validate with paid pre-orders",
                "source_ids": ["S001"],
            }],
            "next_actions": [{
                "action": "Interview ten target customers",
                "priority": "high",
                "due_in_days": 3,
                "success_criteria": "Capture common needs and willingness to pay",
            }],
            "open_questions": ["Which local requirements apply?"],
        },
    }


class TestProjectWorkspaceStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "project_workspace.sqlite3"
        self.store = ProjectWorkspaceStore(self.db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def _create(self, project_id="WS-P1"):
        return self.store.write({
            "operation": "create_from_plan",
            "project_id": project_id,
            "plan_result": _plan_result(),
        })

    def test_create_from_plan_persists_workspace_tasks_and_source_map(self):
        result = self._create()
        self.assertEqual(result["status"], "CREATED")
        workspace = result["workspace"]
        self.assertEqual(workspace["project_id"], "WS-P1")
        self.assertEqual(workspace["status"], "ACTIVE")
        self.assertEqual(workspace["revision"], 1)
        self.assertEqual(workspace["task_tracking"]["task_count"], 4)
        self.assertEqual(workspace["task_tracking"]["progress_percent"], 0)
        self.assertEqual(workspace["sources"][0]["source_id"], "S001")
        self.assertFalse(workspace["decision_grade_evidence"])
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["events"][0]["event_type"], "CREATED_FROM_PLAN")

    def test_workspace_survives_store_recreation_and_can_be_listed(self):
        self._create()
        new_store = ProjectWorkspaceStore(self.db_path)
        fetched = new_store.read({"operation": "get", "project_id": "WS-P1"})
        listed = new_store.read({"operation": "list", "limit": 5})
        self.assertEqual(fetched["status"], "OK")
        self.assertEqual(fetched["workspace"]["goal"], "Validate affordable meal-prep demand")
        self.assertEqual(listed["count"], 1)
        self.assertEqual(listed["projects"][0]["project_id"], "WS-P1")

    def test_create_replay_is_idempotent_but_different_plan_conflicts(self):
        self._create()
        replay = self._create()
        changed = _plan_result()
        changed["plan"]["executive_summary"] = "Changed goal plan"
        conflict = self.store.write({
            "operation": "create_from_plan",
            "project_id": "WS-P1",
            "plan_result": changed,
        })
        self.assertEqual(replay["status"], "IDEMPOTENT_REPLAY")
        self.assertEqual(conflict["status"], "CONFLICT")

    def test_task_update_increments_revision_and_computes_progress(self):
        self._create()
        updated = self.store.write({
            "operation": "update_task",
            "project_id": "WS-P1",
            "expected_revision": 1,
            "task_id": "M01-T01",
            "task_status": "DONE",
            "note": "Customer interviews completed.",
        })
        self.assertEqual(updated["status"], "UPDATED")
        self.assertEqual(updated["revision"], 2)
        self.assertEqual(updated["workspace"]["task_tracking"]["done_task_count"], 1)
        self.assertEqual(updated["workspace"]["task_tracking"]["progress_percent"], 25)
        task = next(t for t in updated["workspace"]["tasks"] if t["task_id"] == "M01-T01")
        self.assertEqual(task["note"], "Customer interviews completed.")
        self.assertEqual(updated["events"][-1]["event_type"], "UPDATE_TASK")

    def test_stale_revision_cannot_overwrite_newer_progress(self):
        self._create()
        first = self.store.write({
            "operation": "update_task", "project_id": "WS-P1",
            "expected_revision": 1, "task_id": "M01-T01",
            "task_status": "IN_PROGRESS",
        })
        stale = self.store.write({
            "operation": "update_task", "project_id": "WS-P1",
            "expected_revision": 1, "task_id": "M01-T02",
            "task_status": "DONE",
        })
        self.assertEqual(first["revision"], 2)
        self.assertEqual(stale["status"], "CONFLICT")
        self.assertEqual(stale["reason"], "project_workspace_revision_mismatch")

    def test_notes_decisions_and_source_refs_are_audited(self):
        self._create()
        note = self.store.write({
            "operation": "append_note", "project_id": "WS-P1",
            "expected_revision": 1, "note": "Supplier quote is still pending.",
            "note_type": "blocker", "author": "operator",
        })
        decision = self.store.write({
            "operation": "record_decision", "project_id": "WS-P1",
            "expected_revision": 2, "title": "Run pre-orders first",
            "rationale": "Limit initial capital risk.", "source_ids": ["S001"],
        })
        self.assertEqual(note["revision"], 2)
        self.assertEqual(decision["revision"], 3)
        self.assertEqual(decision["workspace"]["decisions"][0]["source_ids"], ["S001"])
        invalid = self.store.write({
            "operation": "record_decision", "project_id": "WS-P1",
            "expected_revision": 3, "title": "Bad reference",
            "rationale": "Should fail.", "source_ids": ["S999"],
        })
        with self.assertRaisesRegex(ValueError, "project_workspace_unknown_source_id"):
            self.store.write({
                "operation": "record_decision", "project_id": "WS-P1",
                "expected_revision": 3, "title": "Bad reference",
                "rationale": "Should fail.", "source_ids": ["S999"],
            })
        read = self.store.read({"operation": "get", "project_id": "WS-P1"})
        self.assertEqual([event["event_type"] for event in read["events"]], [
            "CREATED_FROM_PLAN", "APPEND_NOTE", "RECORD_DECISION"
        ])

    def test_completion_requires_resolving_all_tasks_and_archived_is_read_only(self):
        self._create()
        with self.assertRaisesRegex(ValueError, "project_completion_requires_all_tasks_resolved"):
            self.store.write({
                "operation": "update_status", "project_id": "WS-P1",
                "expected_revision": 1, "project_status": "COMPLETED",
            })
        read = self.store.read({"operation": "get", "project_id": "WS-P1"})
        revision = read["revision"]
        for task in read["workspace"]["tasks"]:
            result = self.store.write({
                "operation": "update_task", "project_id": "WS-P1",
                "expected_revision": revision, "task_id": task["task_id"],
                "task_status": "DONE",
            })
            revision = result["revision"]
        completed = self.store.write({
            "operation": "update_status", "project_id": "WS-P1",
            "expected_revision": revision, "project_status": "COMPLETED",
        })
        self.assertEqual(completed["workspace"]["status"], "COMPLETED")
        archived_revision = completed["revision"]
        archived = self.store.write({
            "operation": "update_status", "project_id": "WS-P1",
            "expected_revision": archived_revision, "project_status": "ARCHIVED",
        })
        self.assertEqual(archived["workspace"]["status"], "ARCHIVED")
        with self.assertRaisesRegex(ValueError, "project_workspace_archived"):
            self.store.write({
                "operation": "append_note", "project_id": "WS-P1",
                "expected_revision": archived["revision"], "note": "Archived projects are frozen.",
            })
        with self.assertRaisesRegex(ValueError, "project_workspace_invalid:expected_revision"):
            self.store.write({
                "operation": "append_note", "project_id": "WS-P1",
                "note": "No update without revision.",
            })

    def test_tool_wrappers_separate_reads_from_mutations(self):
        with self.assertRaisesRegex(ValueError, "project_workspace_write_operation_unsupported"):
            project_workspace_write_tool({"operation": "get", "project_id": "WS-P1"}, store=self.store)
        with self.assertRaisesRegex(ValueError, "project_workspace_read_operation_unsupported"):
            project_workspace_read_tool({"operation": "append_note"}, store=self.store)

    def test_incomplete_plan_boundary_is_rejected(self):
        invalid = _plan_result()
        invalid["decision_grade_evidence"] = True
        with self.assertRaisesRegex(ValueError, "project_workspace_plan_boundary_invalid"):
            self.store.write({"operation": "create_from_plan", "project_id": "WS-P1", "plan_result": invalid})


class TestGovernedWorkspaceTools(unittest.TestCase):
    PRINCIPAL = {
        "status": "AUTHENTICATED",
        "authenticated": True,
        "principal": "operator-01",
        "principal_id": "operator-01",
        "scopes": ["run:submit", "job:execute", "governance:evaluate"],
        "roles": ["operator"],
        "auth_method": "test",
    }

    def test_workspace_mutation_requires_explicit_o45_drive_and_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = RealUnifiedRuntime(directory)
            store = ProjectWorkspaceStore(Path(directory) / "workspace.sqlite3")
            calls = []
            runtime.register_execution_tool(
                "provider.project.workspace.write",
                lambda payload: calls.append(dict(payload)) or store.write(payload),
                version="1.0.0",
                retry_safe=False,
            )
            runtime.register_execution_tool(
                "provider.project.workspace.read",
                lambda payload: store.read(payload),
                version="1.0.0",
                retry_safe=True,
            )
            try:
                submitted = runtime.run(
                    run_id="PATCH22-WS-R1",
                    project_id="WS-GOV-P1",
                    strategy_id="PATCH22-WS-S1",
                    intent="Save the generated plan to the persistent workspace",
                    goal="Keep the project plan and progress between sessions",
                    audience="project operator",
                    principal=self.PRINCIPAL,
                    execution_contract={
                        "action": "update_project_workspace",
                        "tool_name": "provider.project.workspace.write",
                        "payload": {
                            "operation": "create_from_plan",
                            "project_id": "WS-GOV-P1",
                            "plan_result": _plan_result(),
                        },
                    },
                )
                governed = submitted["governed_execution"]
                self.assertEqual(governed["status"], "READY")
                self.assertEqual(calls, [])
                executed = runtime.execute_governed_intent(
                    governed["intent"]["intent_id"], principal=self.PRINCIPAL
                )
                self.assertEqual(executed["status"], "SUCCEEDED")
                self.assertEqual(len(calls), 1)
                result = store.read({"operation": "get", "project_id": "WS-GOV-P1"})
                self.assertEqual(result["workspace"]["task_tracking"]["task_count"], 4)
            finally:
                runtime.close()

    def test_workspace_write_action_cannot_bind_to_other_tool(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = RealUnifiedRuntime(directory)
            calls = []
            runtime.register_execution_tool(
                "provider.project.other",
                lambda payload: calls.append(payload) or {"ok": True},
                retry_safe=False,
            )
            try:
                result = runtime.run(
                    run_id="PATCH22-WS-NEG-R1",
                    project_id="WS-NEG-P1",
                    strategy_id="PATCH22-WS-NEG-S1",
                    intent="Attempt an unapproved workspace binding",
                    goal="Test exact binding",
                    principal=self.PRINCIPAL,
                    execution_contract={
                        "action": "update_project_workspace",
                        "tool_name": "provider.project.other",
                        "payload": {"operation": "update_task"},
                    },
                )
                governed = result.get("governed_execution") or {}
                self.assertEqual(governed.get("status"), "BLOCKED")
                self.assertEqual(governed.get("reason"), "project_workspace_action_tool_binding_invalid")
                self.assertEqual(calls, [])
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
