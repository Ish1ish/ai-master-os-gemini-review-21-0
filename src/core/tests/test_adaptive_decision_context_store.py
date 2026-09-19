import tempfile
import unittest

from src.adaptive_decision_context_store import AdaptiveDecisionContextStore


class TestAdaptiveDecisionContextStore(unittest.TestCase):
    def make_store(self):
        return AdaptiveDecisionContextStore(":memory:")

    def context(self):
        return {
            "context_id": "ADC-1",
            "project_id": "P1",
            "advisory_decision": "REFINE",
            "advisory_posture": "ELEVATED_CAUTION",
        }

    def test_record_and_get(self):
        store = self.make_store()
        result = store.record(self.context())
        self.assertEqual(result["status"], "RECORDED")
        self.assertEqual(store.get("ADC-1")["project_id"], "P1")
        store.close()

    def test_same_context_is_idempotent(self):
        store = self.make_store()
        self.assertEqual(store.record(self.context())["status"], "RECORDED")
        self.assertEqual(store.record(self.context())["status"], "IDEMPOTENT_REPLAY")
        store.close()

    def test_same_id_conflict_is_rejected(self):
        store = self.make_store()
        store.record(self.context())
        other = self.context()
        other["advisory_decision"] = "HOLD"
        with self.assertRaises(ValueError):
            store.record(other)
        store.close()

    def test_project_listing(self):
        store = self.make_store()
        store.record(self.context())
        other = self.context()
        other["context_id"] = "ADC-2"
        other["project_id"] = "P2"
        store.record(other)
        rows = store.list_by_project("P1")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["context_id"], "ADC-1")
        store.close()


if __name__ == "__main__":
    unittest.main()
