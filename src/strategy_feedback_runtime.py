from pathlib import Path
from .strategy_feedback_intelligence import StrategyFeedbackIntelligence
from .strategy_feedback_intelligence_store import StrategyFeedbackIntelligenceStore
class StrategyFeedbackRuntime:
    def __init__(self,store_path): self.engine=StrategyFeedbackIntelligence(); self.store=StrategyFeedbackIntelligenceStore(store_path)
    def evaluate(self,*,project_id,strategy_analysis,outcome_assessment):
        a=self.engine.assess(project_id=project_id,analysis_id=strategy_analysis["analysis_id"],selected_strategy_id=strategy_analysis["top_strategy_id"],outcome_quality=outcome_assessment["outcome_quality"],decision_quality=outcome_assessment["decision_quality"],attribution=outcome_assessment["attribution"],evidence_sufficiency=outcome_assessment.get("evidence_sufficiency",0),sample_size=outcome_assessment.get("sample_size",1))
        result=a.to_dict(); self.store.record(result); return result
