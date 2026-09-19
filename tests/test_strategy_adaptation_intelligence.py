import unittest
from src.strategy_adaptation_intelligence import StrategyAdaptationIntelligence

class T(unittest.TestCase):
    def _f(self,signal,e=.9,sid="A"): return {"selected_strategy_id":sid,"signal":signal,"evidence_sufficiency":e}
    def test_positive_maintains(self):
        x=StrategyAdaptationIntelligence().build(project_id="p",strategy_id="A",feedback_items=[self._f("POSITIVE_STRATEGY_SIGNAL")]*3); self.assertEqual(x.recommendation,"MAINTAIN_STRATEGY")
    def test_negative_explores(self):
        x=StrategyAdaptationIntelligence().build(project_id="p",strategy_id="A",feedback_items=[self._f("NEGATIVE_STRATEGY_SIGNAL")]*2+[self._f("REFINE_STRATEGY")]); self.assertEqual(x.recommendation,"EXPLORE_ALTERNATIVE")
    def test_refine_route(self):
        x=StrategyAdaptationIntelligence().build(project_id="p",strategy_id="A",feedback_items=[self._f("REFINE_STRATEGY")]*2+[self._f("POSITIVE_STRATEGY_SIGNAL")]); self.assertEqual(x.recommendation,"REFINE_STRATEGY")
    def test_weak_collects(self):
        x=StrategyAdaptationIntelligence().build(project_id="p",strategy_id="A",feedback_items=[self._f("POSITIVE_STRATEGY_SIGNAL")]*2); self.assertEqual(x.recommendation,"COLLECT_MORE_EVIDENCE")
    def test_do_not_learn_ignored(self):
        x=StrategyAdaptationIntelligence().build(project_id="p",strategy_id="A",feedback_items=[self._f("DO_NOT_LEARN")]*5); self.assertEqual(x.feedback_sample_size,0)
    def test_other_strategy_filtered(self):
        x=StrategyAdaptationIntelligence().build(project_id="p",strategy_id="A",feedback_items=[self._f("NEGATIVE_STRATEGY_SIGNAL",sid="B")]*5); self.assertEqual(x.feedback_sample_size,0)
    def test_caution_preserved(self):
        x=StrategyAdaptationIntelligence().build(project_id="p",strategy_id="A",feedback_items=[self._f("POSITIVE_STRATEGY_SIGNAL")]*3,adaptive_posture="ELEVATED_CAUTION"); self.assertEqual(x.adaptive_posture,"ELEVATED_CAUTION")
    def test_investigation_preserved(self):
        x=StrategyAdaptationIntelligence().build(project_id="p",strategy_id="A",feedback_items=[self._f("POSITIVE_STRATEGY_SIGNAL")]*3,adaptive_posture="INVESTIGATE_EXECUTION"); self.assertEqual(x.recommendation,"REFINE_STRATEGY")
    def test_boundary(self):
        x=StrategyAdaptationIntelligence().build(project_id="p",strategy_id="A",feedback_items=[self._f("POSITIVE_STRATEGY_SIGNAL")]*3); self.assertTrue(x.governance_authoritative); self.assertFalse(x.external_action_executed); self.assertFalse(x.o43_memory_mutated)
    def test_deterministic_id(self):
        a=[self._f("POSITIVE_STRATEGY_SIGNAL")]*3; self.assertEqual(StrategyAdaptationIntelligence().build(project_id="p",strategy_id="A",feedback_items=a).adaptation_id,StrategyAdaptationIntelligence().build(project_id="p",strategy_id="A",feedback_items=a).adaptation_id)
