import tempfile
import unittest

from src.advanced_outcome_analysis_store import AdvancedOutcomeAnalysisStore


class TestAdvancedOutcomeAnalysisStore(unittest.TestCase):
    def sample(self):
        return {
            "analysis_id": "AOA-TEST-001",
            "project_id": "P-AOA",
            "analysis_status": "ANALYZED",
            "sample_size": 3,
            "advisory_route": "MAINTAIN",
        }

    def test_record_and_get(self):
        with tempfile.TemporaryDirectory() as td:
            store = AdvancedOutcomeAnalysisStore(td + "/aoa.sqlite3")
            a = self.sample()
            self.assertEqual(store.record(a)["status"], "RECORDED")
            self.assertEqual(store.get(a["analysis_id"]), a)
            store.close()

    def test_same_analysis_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            store = AdvancedOutcomeAnalysisStore(td + "/aoa.sqlite3")
            a = self.sample()
            store.record(a)
            replay = store.record(a)
            self.assertEqual(replay["status"], "IDEMPOTENT_REPLAY")
            store.close()

    def test_same_id_conflict_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            store = AdvancedOutcomeAnalysisStore(td + "/aoa.sqlite3")
            store.record(self.sample())
            conflict = self.sample()
            conflict["advisory_route"] = "REFINE_DECISION"
            with self.assertRaises(ValueError):
                store.record(conflict)
            store.close()

    def test_project_listing(self):
        with tempfile.TemporaryDirectory() as td:
            store = AdvancedOutcomeAnalysisStore(td + "/aoa.sqlite3")
            store.record(self.sample())
            other = self.sample()
            other["analysis_id"] = "AOA-TEST-002"
            other["project_id"] = "OTHER"
            store.record(other)
            self.assertEqual(len(store.list_by_project("P-AOA")), 1)
            store.close()


if __name__ == "__main__":
    unittest.main()
