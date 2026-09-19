from __future__ import annotations
from dataclasses import dataclass, field
from hashlib import sha256
import json

VALID_SIGNALS={"POSITIVE_STRATEGY_SIGNAL","NEGATIVE_STRATEGY_SIGNAL","REFINE_STRATEGY","DO_NOT_LEARN"}
VALID_POSTURES={"NORMAL","ELEVATED_CAUTION","INVESTIGATE_EXECUTION","COLLECT_MORE_EVIDENCE"}

@dataclass(frozen=True)
class StrategyAdaptationContext:
    adaptation_id:str
    project_id:str
    strategy_id:str
    feedback_sample_size:int
    positive_count:int
    negative_count:int
    refine_count:int
    observed_success_rate:float|None
    evidence_sufficiency:float
    adaptive_posture:str
    recommendation:str
    confidence:str
    governance_authoritative:bool=True
    external_action_executed:bool=False
    o43_memory_mutated:bool=False
    reasons:tuple[str,...]=field(default_factory=tuple)

    def to_dict(self):
        return {
            "adaptation_id":self.adaptation_id,"project_id":self.project_id,"strategy_id":self.strategy_id,
            "feedback_sample_size":self.feedback_sample_size,"positive_count":self.positive_count,
            "negative_count":self.negative_count,"refine_count":self.refine_count,
            "observed_success_rate":self.observed_success_rate,"evidence_sufficiency":self.evidence_sufficiency,
            "adaptive_posture":self.adaptive_posture,"recommendation":self.recommendation,"confidence":self.confidence,
            "governance_authoritative":self.governance_authoritative,"external_action_executed":self.external_action_executed,
            "o43_memory_mutated":self.o43_memory_mutated,"reasons":list(self.reasons),
        }

class StrategyAdaptationIntelligence:
    def _id(self,payload):
        raw=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
        return "SAI-"+sha256(raw).hexdigest()[:24].upper()

    def build(self,*,project_id,strategy_id,feedback_items,adaptive_posture="NORMAL"):
        if not project_id or not strategy_id: raise ValueError("missing required identity")
        if adaptive_posture not in VALID_POSTURES: raise ValueError("invalid adaptive_posture")
        positive=negative=refine=0; used=[]; reasons=[]; evidence_values=[]
        for item in feedback_items:
            if not isinstance(item,dict): raise ValueError("feedback item must be an object")
            sid=item.get("selected_strategy_id")
            if sid != strategy_id: continue
            signal=item.get("signal")
            if signal not in VALID_SIGNALS: raise ValueError("invalid feedback signal")
            if signal=="DO_NOT_LEARN": continue
            used.append(item); evidence_values.append(float(item.get("evidence_sufficiency",0)))
            if signal=="POSITIVE_STRATEGY_SIGNAL": positive+=1
            elif signal=="NEGATIVE_STRATEGY_SIGNAL": negative+=1
            elif signal=="REFINE_STRATEGY": refine+=1
        n=len(used)
        evidence=round(sum(evidence_values)/n,6) if n else 0.0
        success_rate=round(positive/n,6) if n else None
        if n<3 or evidence<0.70:
            recommendation="COLLECT_MORE_EVIDENCE"; confidence="low"; reasons.append("insufficient_strategy_feedback")
            posture="COLLECT_MORE_EVIDENCE"
        elif adaptive_posture=="INVESTIGATE_EXECUTION":
            recommendation="REFINE_STRATEGY"; confidence="medium"; posture="INVESTIGATE_EXECUTION"; reasons.append("execution_mismatch_context_preserved")
        elif adaptive_posture=="ELEVATED_CAUTION":
            posture="ELEVATED_CAUTION"
            if negative>=positive and negative>=2:
                recommendation="EXPLORE_ALTERNATIVE"; confidence="medium"; reasons.append("negative_feedback_under_caution")
            elif refine>=2:
                recommendation="REFINE_STRATEGY"; confidence="medium"; reasons.append("mixed_feedback_under_caution")
            else:
                recommendation="MAINTAIN_STRATEGY"; confidence="medium"; reasons.append("caution_preserved_without_negative_threshold")
        elif negative>=2 and negative>positive:
            recommendation="EXPLORE_ALTERNATIVE"; confidence="high" if evidence>=.9 else "medium"; posture="NORMAL"; reasons.append("negative_feedback_dominates")
        elif refine>=2 and refine>=positive:
            recommendation="REFINE_STRATEGY"; confidence="medium"; posture="NORMAL"; reasons.append("refinement_signal_dominates")
        elif positive>=2 and positive>=negative:
            recommendation="MAINTAIN_STRATEGY"; confidence="high" if evidence>=.9 else "medium"; posture="NORMAL"; reasons.append("positive_feedback_supports_strategy")
        else:
            recommendation="REFINE_STRATEGY"; confidence="medium"; posture="NORMAL"; reasons.append("mixed_strategy_feedback")
        payload={"project_id":project_id,"strategy_id":strategy_id,"feedback_sample_size":n,"positive_count":positive,"negative_count":negative,"refine_count":refine,"observed_success_rate":success_rate,"evidence_sufficiency":evidence,"adaptive_posture":posture,"recommendation":recommendation}
        return StrategyAdaptationContext(self._id(payload),project_id,strategy_id,n,positive,negative,refine,success_rate,evidence,posture,recommendation,confidence,True,False,False,tuple(reasons))
