import unittest

from src.strategy_intelligence_runtime import StrategyIntelligenceRuntime
from src.strategy_intelligence_store import StrategyIntelligenceStore


class TestStrategyIntelligenceRuntime(unittest.TestCase):
    def test_runtime(self):
        store = StrategyIntelligenceStore(":memory:")
        runtime = StrategyIntelligenceRuntime(store)
        ctx = {"context_id": "ADC-1", "project_id": "P1", "advisory_posture": "NORMAL", "advisory_decision": "RECOMMEND"}
        candidates = [{"strategy_id": "A", "prior_success_rate": .9, "sample_size": 8, "execution_mismatch_rate": .0, "evidence_strength": .8, "context_match": .9}]
        r = runtime.rank("P1", decision_context=ctx, candidates=candidates)
        self.assertEqual(r["analysis"]["top_strategy_id"], "A")
        self.assertEqual(r["persistence"]["status"], "RECORDED")
        self.assertTrue(r["governance_unchanged"])
        self.assertFalse(r["external_action_executed"])
        store.close()


if __name__ == "__main__":
    unittest.main()
