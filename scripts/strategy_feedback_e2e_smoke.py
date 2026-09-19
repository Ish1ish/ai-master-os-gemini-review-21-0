import tempfile
from pathlib import Path
from src.strategy_feedback_runtime import StrategyFeedbackRuntime
with tempfile.TemporaryDirectory() as d:
 r=StrategyFeedbackRuntime(Path(d)/'x.sqlite3'); s={'analysis_id':'SIA-A7B0','top_strategy_id':'A'}; o={'outcome_quality':'FULL_SUCCESS','decision_quality':'SOUND_DECISION','attribution':'DECISION','evidence_sufficiency':.9,'sample_size':5}; a=r.evaluate(project_id='demo',strategy_analysis=s,outcome_assessment=o); b=r.evaluate(project_id='demo',strategy_analysis=s,outcome_assessment=o); assert a['feedback_id']==b['feedback_id']; assert r.store.get(a['feedback_id'])==a; assert a['governance_authoritative'] and not a['external_action_executed'] and not a['o43_memory_mutated']
print('V18_STRATEGY_TO_V19_FEEDBACK PASS'); print('V19_FEEDBACK_IDEMPOTENCY PASS'); print('V19_BOUNDARY_INTEGRITY PASS'); print({'feedback_id':a['feedback_id'],'signal':a['signal'],'route':a['advisory_route']}); print('ALL V1.9 END-TO-END CHECKS PASSED.')
