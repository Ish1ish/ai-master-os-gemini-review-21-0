import tempfile
import unittest

from unified_runtime.runtime import UnifiedRunCoordinator


class TestS9UnifiedRunCoordinator(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.coordinator = UnifiedRunCoordinator(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_coordinator_runs_full_journey_and_persists(self):
        result = self.coordinator.run(
            run_id="UR-S9-001",
            project_id="demo",
            strategy_id="STRAT-A",
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["stage_count"], 13)
        self.assertEqual(result["persistence"]["status"], "PERSISTED")
        self.assertEqual(
            result["coordinator_status"],
            "PERSISTED_WITH_REVIEWABLE_MEMORY",
        )

    def test_coordinator_returns_reviewable_memory_proposal(self):
        result = self.coordinator.run(
            run_id="UR-S9-002",
            project_id="demo",
            strategy_id="STRAT-A",
        )
        proposal = result["memory_proposal"]
        self.assertEqual(proposal["status"], "PROPOSAL_ONLY")
        self.assertFalse(proposal["memory_write"])
        self.assertTrue(proposal["human_gate"])
        self.assertEqual(proposal["next_decision"], result["next_decision"])

    def test_same_run_is_idempotent(self):
        first = self.coordinator.run(
            run_id="UR-S9-003",
            project_id="demo",
            strategy_id="STRAT-A",
        )
        second = self.coordinator.run(
            run_id="UR-S9-003",
            project_id="demo",
            strategy_id="STRAT-A",
        )
        self.assertEqual(first["persistence"]["status"], "PERSISTED")
        self.assertEqual(second["persistence"]["status"], "IDEMPOTENT_REPLAY")
        self.assertEqual(
            first["persistence"]["fingerprint"],
            second["persistence"]["fingerprint"],
        )

    def test_identity_survives_coordinator_boundary(self):
        result = self.coordinator.run(
            run_id="UR-S9-004",
            project_id="project-real",
            strategy_id="STRAT-REAL",
        )
        self.assertEqual(result["run_id"], "UR-S9-004")
        self.assertEqual(result["project_id"], "project-real")
        self.assertEqual(result["strategy_id"], "STRAT-REAL")
        self.assertEqual(result["memory_proposal"]["project_id"], "project-real")

    def test_next_decision_survives_persistence_and_handoff(self):
        result = self.coordinator.run(
            run_id="UR-S9-005",
            project_id="demo",
            strategy_id="STRAT-A",
        )
        self.assertEqual(
            result["persistence"]["status"],
            "PERSISTED",
        )
        self.assertEqual(
            result["memory_proposal"]["next_decision"],
            result["next_decision"],
        )

    def test_coordinator_does_not_enable_external_action(self):
        result = self.coordinator.run(
            run_id="UR-S9-006",
            project_id="demo",
            strategy_id="STRAT-A",
        )
        self.assertFalse(result["external_action"])
        self.assertFalse(result["memory_write"])
        self.assertFalse(result["governance_mutation"])
        self.assertFalse(result["memory_proposal"]["memory_write"])

    def test_true_conflict_is_visible(self):
        first = self.coordinator.run(
            run_id="UR-S9-007",
            project_id="demo",
            strategy_id="STRAT-A",
        )
        self.assertEqual(first["persistence"]["status"], "PERSISTED")

        # Reproduce a conflict by calling the persistence layer with a changed
        # next decision for the same identity.
        altered = dict(first)
        altered["next_decision"] = {
            "run_id": "UR-S9-007",
            "project_id": "demo",
            "strategy_id": "STRAT-A",
            "route": "EXPLORE_ALTERNATIVE",
            "reason": "conflict-test",
        }
        conflict = self.coordinator.persistence.persist(altered)
        self.assertEqual(conflict["status"], "CONFLICT")
        self.assertEqual(
            self.coordinator.persistence.get("UR-S9-007", "demo")["fingerprint"],
            first["persistence"]["fingerprint"],
        )

    def test_multiple_projects_remain_isolated(self):
        a = self.coordinator.run(
            run_id="UR-S9-008",
            project_id="project-a",
            strategy_id="STRAT-A",
        )
        b = self.coordinator.run(
            run_id="UR-S9-008",
            project_id="project-b",
            strategy_id="STRAT-B",
        )
        self.assertEqual(a["persistence"]["status"], "PERSISTED")
        self.assertEqual(b["persistence"]["status"], "PERSISTED")
        self.assertNotEqual(
            a["persistence"]["fingerprint"],
            b["persistence"]["fingerprint"],
        )

    def test_coordinator_is_repeatable(self):
        first = self.coordinator.run(
            run_id="UR-S9-009",
            project_id="demo",
            strategy_id="STRAT-A",
        )
        second = self.coordinator.run(
            run_id="UR-S9-009",
            project_id="demo",
            strategy_id="STRAT-A",
        )
        self.assertEqual(first["next_decision"], second["next_decision"])
        self.assertEqual(first["memory_proposal"], second["memory_proposal"])


if __name__ == "__main__":
    unittest.main()
