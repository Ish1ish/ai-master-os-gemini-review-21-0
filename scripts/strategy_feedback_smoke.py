from src.strategy_feedback_intelligence import StrategyFeedbackIntelligence
e=StrategyFeedbackIntelligence(); a=e.assess(project_id='demo',analysis_id='SIA-DEMO',selected_strategy_id='A',outcome_quality='FULL_SUCCESS',decision_quality='SOUND_DECISION',attribution='DECISION',evidence_sufficiency=.95,sample_size=6)
assert a.signal=='POSITIVE_STRATEGY_SIGNAL' and a.advisory_route=='MAINTAIN_STRATEGY' and a.governance_authoritative and not a.external_action_executed and not a.o43_memory_mutated
b=e.assess(project_id='demo',analysis_id='SIA-DEMO',selected_strategy_id='A',outcome_quality='FULL_SUCCESS',decision_quality='SOUND_DECISION',attribution='DECISION',evidence_sufficiency=.99,sample_size=2)
assert b.signal=='DO_NOT_LEARN' and b.advisory_route=='COLLECT_MORE_EVIDENCE'
print('STRATEGY FEEDBACK INTELLIGENCE SMOKE PASS'); print(a.to_dict()); print('FEEDBACK_SIGNAL PASS'); print('EVIDENCE_GATE PASS'); print('ADVISORY_BOUNDARY PASS'); print('ALL STRATEGY FEEDBACK CHECKS PASSED.')
