import os
import tempfile
import unittest

from src.evidence_loop import ValidationEvidenceLoop, build_experiment_from_decision_surface
from src.experiment_store import ExperimentStore


class TestO42ValidationEvidenceLoop(unittest.TestCase):
    def _definition(self):
        return {
            "experiment_id": "VAL-001",
            "hypothesis": "Customers experience recurring pain.",
            "sample_size": 10,
            "success_threshold": {
                "problem_confirmation": {"operator": ">=", "value": 6},
                "high_intent": {"operator": ">=", "value": 3},
            },
            "no_go_thresholds": {
                "problem_confirmation": {"operator": "<", "value": 4, "reason": "Problem confirmation too weak."}
            },
        }

    def test_go_when_all_thresholds_met(self):
        out = ValidationEvidenceLoop().evaluate(self._definition(), {
            "sample_size": 10,
            "metrics": {"problem_confirmation": 7, "high_intent": 4},
            "evidence_refs": ["INT-001", "INT-010"],
        })
        self.assertEqual(out["decision"], "GO")
        self.assertEqual(out["confidence"], "high")

    def test_refine_when_complete_but_threshold_missed(self):
        out = ValidationEvidenceLoop().evaluate(self._definition(), {
            "sample_size": 10,
            "metrics": {"problem_confirmation": 6, "high_intent": 2},
            "evidence_refs": ["INT-001", "INT-010"],
        })
        self.assertEqual(out["decision"], "REFINE")
        self.assertTrue(out["completed"])

    def test_no_go_threshold(self):
        out = ValidationEvidenceLoop().evaluate(self._definition(), {
            "sample_size": 10,
            "metrics": {"problem_confirmation": 3, "high_intent": 0},
            "evidence_refs": ["INT-001", "INT-010"],
        })
        self.assertEqual(out["decision"], "NO-GO")

    def test_inconclusive_without_evidence_refs(self):
        out = ValidationEvidenceLoop().evaluate(self._definition(), {
            "sample_size": 10,
            "metrics": {"problem_confirmation": 8, "high_intent": 4},
            "evidence_refs": [],
        })
        self.assertEqual(out["decision"], "INCONCLUSIVE")
        self.assertIn(out["confidence"], {"low", "medium"})

    def test_inconclusive_when_sample_incomplete(self):
        out = ValidationEvidenceLoop().evaluate(self._definition(), {
            "sample_size": 4,
            "metrics": {"problem_confirmation": 3, "high_intent": 1},
            "evidence_refs": ["INT-001"],
        })
        self.assertEqual(out["decision"], "INCONCLUSIVE")

    def test_legacy_string_thresholds_are_normalized(self):
        definition = {
            "sample_size": 10,
            "success_threshold": {
                "problem_confirmation": "At least 6/10 report the problem as recurring and material.",
                "high_intent": "At least 3/10 agree to a pilot, test, or concrete next step.",
            },
        }
        out = ValidationEvidenceLoop().evaluate(definition, {
            "sample_size": 10,
            "metrics": {"problem_confirmation": 6, "high_intent": 3},
            "evidence_refs": ["INT-001", "INT-010"],
        })
        self.assertEqual(out["decision"], "GO")

    def test_build_experiment_from_decision_surface_preserves_scores(self):
        surface = {
            "recommendation": "Narrow AI workflow automation",
            "customer": "Egyptian SMEs",
            "problem": "Recurring workflow work",
            "desired_outcome": "Reduce manual work",
            "opportunity_score": 6,
            "strategy_score": 7.7,
            "confidence": "medium",
            "evidence_boundary": "local_evidence_supported",
            "validation_experiment": {
                "experiment_id": "VAL-JOB",
                "hypothesis": "SMEs experience recurring workflow pain.",
                "sample_size": 10,
                "method": "Interview 10 SMEs",
                "success_threshold": {"problem_confirmation": "At least 6/10"},
                "decision_rule": "GO when threshold is met; otherwise refine.",
            },
        }
        definition = build_experiment_from_decision_surface(surface, "JOB-1", "PROJ-1", "ar")
        self.assertEqual(definition["decision_context"]["opportunity_score"], 6)
        self.assertEqual(definition["decision_context"]["strategy_score"], 7.7)
        self.assertIn("thresholds_machine", definition)
        self.assertIn("re_run_context", ValidationEvidenceLoop().evaluate(definition, {"sample_size":10,"metrics":{"problem_confirmation":6},"evidence_refs":["E1"]}))


class TestO42ExperimentStore(unittest.TestCase):
    def test_create_record_evidence_and_evaluation_persist(self):
        with tempfile.TemporaryDirectory() as td:
            store = ExperimentStore(os.path.join(td, "experiments.sqlite3"))
            exp = store.create({"experiment_id": "EXP-001", "sample_size": 2}, "PROJ-1", "JOB-1")
            self.assertEqual(exp["status"], "READY")
            stored = store.save_evidence("EXP-001", {"sample_size": 2, "metrics": {"x": 2}, "evidence_refs": ["E-1"]})
            self.assertEqual(stored["status"], "EVIDENCE_RECORDED")
            stored = store.save_evaluation("EXP-001", {"decision": "GO", "summary": "ok"})
            self.assertEqual(stored["status"], "CONCLUDED")
            reopened = store.get("EXP-001")
            self.assertEqual(reopened["decision"], "GO")
            self.assertEqual(reopened["evidence"]["metrics"]["x"], 2)
            store.close()

    def test_idempotent_create_from_same_id_is_blocked_by_sqlite(self):
        with tempfile.TemporaryDirectory() as td:
            store = ExperimentStore(os.path.join(td, "experiments.sqlite3"))
            store.create({"experiment_id": "EXP-001"}, "PROJ-1")
            with self.assertRaises(Exception):
                store.create({"experiment_id": "EXP-001"}, "PROJ-1")
            store.close()


if __name__ == "__main__":
    unittest.main()
