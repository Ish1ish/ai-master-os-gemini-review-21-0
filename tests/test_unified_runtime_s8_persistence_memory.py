import tempfile
import unittest
from pathlib import Path

from unified_runtime.golden_run import GoldenUnifiedRun
from unified_runtime.persistence import UnifiedMemoryHandoff, UnifiedRunPersistence


class TestS8PersistentTraceMemoryHandoff(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = UnifiedRunPersistence(self.tmp.name)
        self.run = GoldenUnifiedRun().run(
            run_id="UR-S8-001",
            project_id="demo",
            strategy_id="STRAT-A",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_persist_and_reload_run(self):
        result = self.store.persist(self.run)
        self.assertEqual(result["status"], "PERSISTED")
        loaded = self.store.get("UR-S8-001", "demo")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["run_id"], "UR-S8-001")
        self.assertEqual(loaded["project_id"], "demo")

    def test_same_run_is_idempotent(self):
        first = self.store.persist(self.run)
        second = self.store.persist(self.run)
        self.assertEqual(first["status"], "PERSISTED")
        self.assertEqual(second["status"], "IDEMPOTENT_REPLAY")
        self.assertEqual(first["fingerprint"], second["fingerprint"])

    def test_true_identity_conflict_is_rejected(self):
        self.store.persist(self.run)
        changed = dict(self.run)
        changed["next_decision"] = {
            "route": "EXPLORE_ALTERNATIVE",
            "reason": "changed",
        }
        result = self.store.persist(changed)
        self.assertEqual(result["status"], "CONFLICT")
        self.assertNotEqual(result["fingerprint"], result["existing_fingerprint"])

    def test_different_project_is_separate_identity(self):
        changed = dict(self.run)
        changed["project_id"] = "project-b"
        result = self.store.persist(changed)
        self.assertEqual(result["status"], "PERSISTED")
        self.assertIsNotNone(self.store.get("UR-S8-001", "project-b"))

    def test_memory_handoff_is_proposal_only(self):
        proposal = UnifiedMemoryHandoff().propose(self.run)
        self.assertEqual(proposal["status"], "PROPOSAL_ONLY")
        self.assertFalse(proposal["memory_write"])
        self.assertTrue(proposal["human_gate"])
        self.assertEqual(proposal["project_id"], "demo")
        self.assertEqual(proposal["run_id"], "UR-S8-001")

    def test_memory_proposal_preserves_next_decision(self):
        proposal = UnifiedMemoryHandoff().propose(self.run)
        self.assertEqual(
            proposal["next_decision"],
            self.run["next_decision"],
        )
        self.assertEqual(
            proposal["adaptation_recommendation"],
            self.run["stages"]["ADAPTATION"]["recommendation"],
        )

    def test_trace_file_is_compact_and_structured(self):
        self.store.persist(self.run)
        lines = Path(self.store.trace_path).read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        self.assertIn('"run_id": "UR-S8-001"', lines[0])
        self.assertIn('"project_id": "demo"', lines[0])

    def test_fingerprint_is_deterministic(self):
        a = self.store.fingerprint(self.run)
        b = self.store.fingerprint(self.run)
        self.assertEqual(a, b)

    def test_missing_identity_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "run_id_and_project_id_are_required"):
            self.store.persist({"status": "PASS"})

    def test_reload_missing_run_returns_none(self):
        self.assertIsNone(self.store.get("missing", "demo"))


if __name__ == "__main__":
    unittest.main()
