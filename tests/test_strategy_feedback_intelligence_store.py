import tempfile,unittest
from pathlib import Path
from src.strategy_feedback_intelligence import StrategyFeedbackIntelligence
from src.strategy_feedback_intelligence_store import StrategyFeedbackIntelligenceStore
class T(unittest.TestCase):
 def setUp(self):
  self.d=tempfile.TemporaryDirectory(); self.s=StrategyFeedbackIntelligenceStore(Path(self.d.name)/'x.sqlite3')
  self.p=StrategyFeedbackIntelligence().assess(project_id='p',analysis_id='a',selected_strategy_id='A',outcome_quality='FULL_SUCCESS',decision_quality='SOUND_DECISION',attribution='DECISION',evidence_sufficiency=.9,sample_size=5).to_dict()
 def tearDown(self): self.d.cleanup()
 def test_record_get(self): self.assertEqual(self.s.record(self.p),self.p); self.assertEqual(self.s.get(self.p['feedback_id']),self.p)
 def test_idempotent(self): self.assertEqual(self.s.record(self.p),self.s.record(self.p))
 def test_conflict(self):
  self.s.record(self.p); q=dict(self.p); q['signal']='REFINE_STRATEGY';
  with self.assertRaises(ValueError): self.s.record(q)
