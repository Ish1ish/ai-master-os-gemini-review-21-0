from __future__ import annotations
from dataclasses import dataclass, field
from hashlib import sha256
import json

VALID_OUTCOMES={"FULL_SUCCESS","PARTIAL_SUCCESS","MISSED_TARGET","FAILED","INCONCLUSIVE"}
VALID_ATTRIBUTIONS={"DECISION","ROUTING","EXECUTION","TOOL","GOVERNANCE","INSUFFICIENT_EVIDENCE"}
VALID_DECISIONS={"SOUND_DECISION","TARGET_MISSED","EXECUTION_MISMATCH","INSUFFICIENT_EVIDENCE","UNRESOLVED"}

@dataclass(frozen=True)
class StrategyFeedbackAssessment:
    feedback_id:str; project_id:str; analysis_id:str; selected_strategy_id:str
    outcome_quality:str; decision_quality:str; attribution:str
    evidence_sufficiency:float; sample_size:int; signal:str; advisory_route:str
    confidence:str; governance_authoritative:bool=True; external_action_executed:bool=False
    o43_memory_mutated:bool=False; reasons:tuple[str,...]=field(default_factory=tuple)
    def to_dict(self):
        return {"feedback_id":self.feedback_id,"project_id":self.project_id,"analysis_id":self.analysis_id,
        "selected_strategy_id":self.selected_strategy_id,"outcome_quality":self.outcome_quality,
        "decision_quality":self.decision_quality,"attribution":self.attribution,
        "evidence_sufficiency":self.evidence_sufficiency,"sample_size":self.sample_size,
        "signal":self.signal,"advisory_route":self.advisory_route,"confidence":self.confidence,
        "governance_authoritative":self.governance_authoritative,"external_action_executed":self.external_action_executed,
        "o43_memory_mutated":self.o43_memory_mutated,"reasons":list(self.reasons)}

class StrategyFeedbackIntelligence:
    def _id(self,payload):
        raw=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
        return "SFI-"+sha256(raw).hexdigest()[:24].upper()
    def assess(self,*,project_id,analysis_id,selected_strategy_id,outcome_quality,decision_quality,attribution,evidence_sufficiency,sample_size=1):
        if not all((project_id,analysis_id,selected_strategy_id)): raise ValueError("missing required identity")
        if outcome_quality not in VALID_OUTCOMES: raise ValueError("invalid outcome_quality")
        if decision_quality not in VALID_DECISIONS: raise ValueError("invalid decision_quality")
        if attribution not in VALID_ATTRIBUTIONS: raise ValueError("invalid attribution")
        evidence=float(evidence_sufficiency)
        if not 0<=evidence<=1: raise ValueError("invalid evidence_sufficiency")
        if sample_size<1: raise ValueError("invalid sample_size")
        signal="DO_NOT_LEARN"; route="COLLECT_MORE_EVIDENCE"; reasons=[]
        if outcome_quality=="INCONCLUSIVE" or attribution=="INSUFFICIENT_EVIDENCE":
            reasons.append("insufficient_outcome_evidence")
        elif sample_size<3 or evidence<0.70:
            reasons.append("insufficient_sample_or_evidence")
        elif attribution in {"EXECUTION","TOOL","GOVERNANCE"}:
            reasons.append("outcome_not_attributable_to_strategy_selection")
        elif outcome_quality=="FULL_SUCCESS" and decision_quality=="SOUND_DECISION" and attribution in {"DECISION","ROUTING"}:
            signal="POSITIVE_STRATEGY_SIGNAL"; route="MAINTAIN_STRATEGY"; reasons.append("strategy_selection_supported")
        elif outcome_quality in {"MISSED_TARGET","FAILED"} or decision_quality=="TARGET_MISSED":
            signal="NEGATIVE_STRATEGY_SIGNAL"; route="REFINE_STRATEGY"; reasons.append("negative_strategy_outcome_signal")
        elif outcome_quality=="PARTIAL_SUCCESS" or decision_quality in {"EXECUTION_MISMATCH","UNRESOLVED"}:
            signal="REFINE_STRATEGY"; route="REFINE_STRATEGY"; reasons.append("mixed_or_unresolved_strategy_signal")
        else:
            reasons.append("strategy_feedback_not_attributable")
        confidence="high" if evidence>=.9 and sample_size>=5 else "medium" if evidence>=.7 and sample_size>=3 else "low"
        payload={"project_id":project_id,"analysis_id":analysis_id,"selected_strategy_id":selected_strategy_id,"outcome_quality":outcome_quality,"decision_quality":decision_quality,"attribution":attribution,"evidence_sufficiency":round(evidence,6),"sample_size":sample_size,"signal":signal,"route":route}
        return StrategyFeedbackAssessment(self._id(payload),project_id,analysis_id,selected_strategy_id,outcome_quality,decision_quality,attribution,evidence,sample_size,signal,route,confidence,True,False,False,tuple(reasons))
