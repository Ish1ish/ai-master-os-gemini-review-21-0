import tempfile,unittest
from pathlib import Path
from src.strategy_feedback_runtime import StrategyFeedbackRuntime
class T(unittest.TestCase):
 def test_runtime(self):
  with tempfile.TemporaryDirectory() as d:
   r=StrategyFeedbackRuntime(Path(d)/'x.sqlite3'); x=r.evaluate(project_id='p',strategy_analysis={'analysis_id':'a','top_strategy_id':'A'},outcome_assessment={'outcome_quality':'FULL_SUCCESS','decision_quality':'SOUND_DECISION','attribution':'DECISION','evidence_sufficiency':.9,'sample_size':5})
   self.assertEqual(x['signal'],'POSITIVE_STRATEGY_SIGNAL'); self.assertTrue(x['governance_authoritative']); self.assertFalse(x['external_action_executed']); self.assertFalse(x['o43_memory_mutated'])
