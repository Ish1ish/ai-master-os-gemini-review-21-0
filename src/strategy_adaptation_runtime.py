from __future__ import annotations
from .strategy_adaptation_intelligence import StrategyAdaptationIntelligence
from .strategy_adaptation_store import StrategyAdaptationStore

class StrategyAdaptationRuntime:
    def __init__(self,store): self.store=store
    def evaluate(self,*,project_id,strategy_id,feedback_items,adaptive_posture="NORMAL"):
        ctx=StrategyAdaptationIntelligence().build(project_id=project_id,strategy_id=strategy_id,feedback_items=feedback_items,adaptive_posture=adaptive_posture)
        self.store.record(ctx)
        return ctx
