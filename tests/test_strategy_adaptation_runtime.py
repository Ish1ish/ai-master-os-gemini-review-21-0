import tempfile,unittest
from src.strategy_adaptation_store import StrategyAdaptationStore
from src.strategy_adaptation_runtime import StrategyAdaptationRuntime
class T(unittest.TestCase):
    def test_runtime(self):
        with tempfile.TemporaryDirectory() as d:
            r=StrategyAdaptationRuntime(StrategyAdaptationStore(d+r"\x.sqlite3"))
            x=r.evaluate(project_id="p",strategy_id="A",feedback_items=[{"selected_strategy_id":"A","signal":"POSITIVE_STRATEGY_SIGNAL","evidence_sufficiency":.9}]*3)
            self.assertEqual(x.recommendation,"MAINTAIN_STRATEGY")
            self.assertFalse(x.external_action_executed)
