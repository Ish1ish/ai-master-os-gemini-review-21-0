import unittest

from src.strategy_intelligence import StrategyIntelligence


class TestStrategyIntelligence(unittest.TestCase):
    def setUp(self):
        self.engine = StrategyIntelligence()
        self.ctx = {
            "context_id": "ADC-1",
            "project_id": "P1",
            "advisory_posture": "NORMAL",
            "advisory_decision": "RECOMMEND",
        }
        self.candidates = [
            {"strategy_id": "A", "prior_success_rate": .8, "sample_size": 8, "execution_mismatch_rate": .1, "evidence_strength": .8, "context_match": .9},
            {"strategy_id": "B", "prior_success_rate": .6, "sample_size": 7, "execution_mismatch_rate": .0, "evidence_strength": .9, "context_match": .6},
        ]

    def test_ranking_is_deterministic(self):
        x = self.engine.rank(project_id="P1", decision_context=self.ctx, candidates=self.candidates)
        y = self.engine.rank(project_id="P1", decision_context=self.ctx, candidates=self.candidates)
        self.assertEqual(x["analysis_id"], y["analysis_id"])
        self.assertEqual(x["ranked_strategies"], y["ranked_strategies"])

    def test_top_strategy_is_selected_advisory(self):
        x = self.engine.rank(project_id="P1", decision_context=self.ctx, candidates=self.candidates)
        self.assertEqual(x["route"], "RANKED_ADVISORY")
        self.assertEqual(x["top_strategy_id"], "A")

    def test_weak_evidence_holds(self):
        x = self.engine.rank(project_id="P1", decision_context=self.ctx, candidates=self.candidates, evidence_sufficient=False)
        self.assertEqual(x["route"], "COLLECT_MORE_EVIDENCE")
        self.assertIsNone(x["top_strategy_id"])

    def test_caution_reduces_scores(self):
        ctx = dict(self.ctx)
        ctx["advisory_posture"] = "ELEVATED_CAUTION"
        x = self.engine.rank(project_id="P1", decision_context=ctx, candidates=self.candidates)
        self.assertLess(x["ranked_strategies"][0]["score"], .9)

    def test_project_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            self.engine.rank(project_id="P2", decision_context=self.ctx, candidates=self.candidates)

    def test_governance_boundary(self):
        x = self.engine.rank(project_id="P1", decision_context=self.ctx, candidates=self.candidates)
        self.assertEqual(x["governance_authority"], "POLICY_AND_GOVERNANCE_REMAIN_AUTHORITATIVE")
        self.assertFalse(x["external_action_executed"])
        self.assertFalse(x["o43_memory_mutated"])

    def test_empty_candidates_rejected(self):
        with self.assertRaises(ValueError):
            self.engine.rank(project_id="P1", decision_context=self.ctx, candidates=[])


if __name__ == "__main__":
    unittest.main()
