import os
import tempfile
import unittest

from src.outcome_intelligence_store import OutcomeIntelligenceStore
from src.learning_signal_adapter import to_o43_lesson


class TestOutcomeIntelligencePersistence(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.store = OutcomeIntelligenceStore(
            os.path.join(self.td.name, "outcome_intelligence.sqlite3")
        )
        self.assessment = {
            "assessment_id": "OIA-ABC123",
            "trace_id": "TRC-001",
            "project_id": "P1",
            "outcome_quality": "FULL_SUCCESS",
            "decision_quality": "SOUND_DECISION",
            "attribution": "DECISION",
            "learning_signal": "POSITIVE_CALIBRATION",
            "outcome_success": True,
            "confidence": "high",
            "evidence_refs": ["EVID-1"],
            "evidence_sufficient": True,
        }

    def tearDown(self):
        self.store.close()
        self.td.cleanup()

    def test_record_and_get(self):
        out = self.store.record(self.assessment)
        self.assertEqual(out["status"], "RECORDED")
        self.assertEqual(
            self.store.get("OIA-ABC123")["trace_id"],
            "TRC-001",
        )

    def test_same_assessment_is_idempotent(self):
        self.assertEqual(self.store.record(self.assessment)["status"], "RECORDED")
        replay = self.store.record(dict(self.assessment))
        self.assertEqual(replay["status"], "IDEMPOTENT_REPLAY")

    def test_same_id_conflict_is_rejected(self):
        self.store.record(self.assessment)
        changed = dict(self.assessment)
        changed["learning_signal"] = "REFINE"
        with self.assertRaises(ValueError):
            self.store.record(changed)

    def test_project_listing(self):
        self.store.record(self.assessment)
        rows = self.store.list_by_project("P1")
        self.assertEqual(len(rows), 1)

    def test_learning_signal_becomes_o43_lesson(self):
        lesson = to_o43_lesson(self.assessment)
        self.assertEqual(lesson["decision"], "GO")
        self.assertEqual(lesson["lesson_id"], "OIL-LESSON-ABC123")
        self.assertEqual(lesson["provenance"]["trace_id"], "TRC-001")

    def test_do_not_learn_never_becomes_lesson(self):
        blocked = dict(self.assessment)
        blocked["learning_signal"] = "DO_NOT_LEARN"
        self.assertIsNone(to_o43_lesson(blocked))

    def test_evidence_gate_blocks_lesson(self):
        blocked = dict(self.assessment)
        blocked["evidence_sufficient"] = False
        self.assertIsNone(to_o43_lesson(blocked))


if __name__ == "__main__":
    unittest.main()
