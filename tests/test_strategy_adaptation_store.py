import tempfile,unittest
from src.strategy_adaptation_intelligence import StrategyAdaptationIntelligence
from src.strategy_adaptation_store import StrategyAdaptationStore
class T(unittest.TestCase):
    def setUp(self): self.d=tempfile.TemporaryDirectory(); self.s=StrategyAdaptationStore(self.d.name+r"\x.sqlite3")
    def tearDown(self): self.d.cleanup()
    def _ctx(self): return StrategyAdaptationIntelligence().build(project_id="p",strategy_id="A",feedback_items=[{"selected_strategy_id":"A","signal":"POSITIVE_STRATEGY_SIGNAL","evidence_sufficiency":.9}]*3)
    def test_record_get(self):
        c=self._ctx(); self.s.record(c); self.assertEqual(self.s.get(c.adaptation_id)["strategy_id"],"A")
    def test_idempotent(self):
        c=self._ctx(); self.s.record(c); self.assertEqual(self.s.record(c).adaptation_id,c.adaptation_id)
    def test_conflict(self):
        c=self._ctx(); self.s.record(c); bad=self._ctx().to_dict(); bad["recommendation"]="EXPLORE_ALTERNATIVE"; from src.strategy_adaptation_intelligence import StrategyAdaptationContext; b=StrategyAdaptationContext(**{**c.__dict__,"recommendation":"EXPLORE_ALTERNATIVE"}); b=b; 
        with self.assertRaises(ValueError): self.s.record(b)
    def test_list_project(self):
        c=self._ctx(); self.s.record(c); self.assertEqual(len(self.s.list_project("p")),1)
