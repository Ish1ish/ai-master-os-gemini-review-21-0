from src.strategy_adaptation_intelligence import StrategyAdaptationIntelligence
f=[{"selected_strategy_id":"A","signal":"POSITIVE_STRATEGY_SIGNAL","evidence_sufficiency":.95}]*5
x=StrategyAdaptationIntelligence().build(project_id="demo",strategy_id="A",feedback_items=f)
assert x.recommendation=="MAINTAIN_STRATEGY"; assert x.governance_authoritative; assert not x.external_action_executed and not x.o43_memory_mutated
print("STRATEGY ADAPTATION INTELLIGENCE SMOKE PASS")
print(x.to_dict())
print("FEEDBACK_TO_ADAPTATION PASS")
print("ADVISORY_BOUNDARY PASS")
print("ALL STRATEGY ADAPTATION CHECKS PASSED.")
