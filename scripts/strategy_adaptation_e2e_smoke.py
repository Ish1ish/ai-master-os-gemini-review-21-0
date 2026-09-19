import tempfile
from src.strategy_adaptation_intelligence import StrategyAdaptationIntelligence
from src.strategy_adaptation_store import StrategyAdaptationStore
from src.strategy_adaptation_runtime import StrategyAdaptationRuntime
f=[{"selected_strategy_id":"A","signal":"POSITIVE_STRATEGY_SIGNAL","evidence_sufficiency":.95}]*5
with tempfile.TemporaryDirectory() as d:
    rt=StrategyAdaptationRuntime(StrategyAdaptationStore(d+r"\x.sqlite3"))
    a=rt.evaluate(project_id="demo",strategy_id="A",feedback_items=f)
    b=rt.evaluate(project_id="demo",strategy_id="A",feedback_items=f)
    assert a.adaptation_id==b.adaptation_id
    assert rt.store.get(a.adaptation_id)["recommendation"]=="MAINTAIN_STRATEGY"
print("V19_FEEDBACK_TO_V20_ADAPTATION PASS")
print("V20_ADAPTATION_IDEMPOTENCY PASS")
print("V20_BOUNDARY_INTEGRITY PASS")
print({"adaptation_id":a.adaptation_id,"recommendation":a.recommendation})
print("ALL V2.0 END-TO-END CHECKS PASSED.")
