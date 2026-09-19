import unittest

from src.strategy_intelligence_store import StrategyIntelligenceStore


class TestStrategyIntelligenceStore(unittest.TestCase):
    def sample(self):
        return {"analysis_id": "SIA-1", "project_id": "P1", "route": "RANKED_ADVISORY", "top_strategy_id": "A"}

    def test_record_and_get(self):
        s = StrategyIntelligenceStore(":memory:")
        self.assertEqual(s.record(self.sample())["status"], "RECORDED")
        self.assertEqual(s.get("SIA-1")["top_strategy_id"], "A")
        s.close()

    def test_idempotency(self):
        s = StrategyIntelligenceStore(":memory:")
        s.record(self.sample())
        self.assertEqual(s.record(self.sample())["status"], "IDEMPOTENT_REPLAY")
        s.close()

    def test_conflict(self):
        s = StrategyIntelligenceStore(":memory:")
        s.record(self.sample())
        x = self.sample()
        x["top_strategy_id"] = "B"
        with self.assertRaises(ValueError):
            s.record(x)
        s.close()


if __name__ == "__main__":
    unittest.main()
