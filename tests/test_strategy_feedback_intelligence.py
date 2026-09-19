import unittest
from src.strategy_feedback_intelligence import StrategyFeedbackIntelligence
class T(unittest.TestCase):
 def setUp(self): self.e=StrategyFeedbackIntelligence(); self.k=dict(project_id='p',analysis_id='a',selected_strategy_id='A',outcome_quality='FULL_SUCCESS',decision_quality='SOUND_DECISION',attribution='DECISION',evidence_sufficiency=.95,sample_size=6)
 def test_positive(self): self.assertEqual(self.e.assess(**self.k).signal,'POSITIVE_STRATEGY_SIGNAL')
 def test_negative(self): self.assertEqual(self.e.assess(**{**self.k,'outcome_quality':'MISSED_TARGET','decision_quality':'TARGET_MISSED'}).signal,'NEGATIVE_STRATEGY_SIGNAL')
 def test_partial(self): self.assertEqual(self.e.assess(**{**self.k,'outcome_quality':'PARTIAL_SUCCESS','decision_quality':'UNRESOLVED'}).signal,'REFINE_STRATEGY')
 def test_weak(self): self.assertEqual(self.e.assess(**{**self.k,'sample_size':2}).signal,'DO_NOT_LEARN')
 def test_inconclusive(self): self.assertEqual(self.e.assess(**{**self.k,'outcome_quality':'INCONCLUSIVE','attribution':'INSUFFICIENT_EVIDENCE'}).signal,'DO_NOT_LEARN')
 def test_execution_not_blame(self): self.assertEqual(self.e.assess(**{**self.k,'outcome_quality':'FAILED','decision_quality':'EXECUTION_MISMATCH','attribution':'EXECUTION'}).signal,'DO_NOT_LEARN')
 def test_deterministic_id(self): self.assertEqual(self.e.assess(**self.k).feedback_id,self.e.assess(**self.k).feedback_id)
 def test_boundary(self):
  a=self.e.assess(**self.k); self.assertTrue(a.governance_authoritative); self.assertFalse(a.external_action_executed); self.assertFalse(a.o43_memory_mutated)
