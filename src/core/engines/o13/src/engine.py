from .options import BusinessModelBuilder
from .positioning import build_positioning
from .risk import build_risk_map
from .mvp import MVPPlanner
from .decision import build_strategy_score, select_strategy
from .plan import build_90_day_plan
from .qa import validate_strategy_output
from src.handoff_contracts import (
    build_strategy_to_product_handoff,
    build_idea_to_strategy_handoff,
    validate_semantic_handoff,
    compact_semantic_text,
)
import re


def _compact_evidence_text(text: str, limit: int = 240) -> str:
    value = re.sub(r"\s+", " ", str(text or "").strip())
    if not value:
        return "market evidence"
    if "|" in value:
        cells = [c.strip() for c in value.split("|") if c.strip()]
        cells = [c for c in cells if not re.fullmatch(r"[-: ]+", c)]
        value = " — ".join(cells[:4]) if cells else "market evidence"
    value = re.sub(r"#{1,6}\s*", "", value).strip(" -|:")
    if len(value) > limit:
        value = value[:limit].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"
    return value


def _build_idea_handoff(idea):
    return build_idea_to_strategy_handoff(idea)


class RealStrategyEngine:
    def __init__(self):
        self.model_builder=BusinessModelBuilder()
        self.mvp=MVPPlanner()

    def build(self,idea,market_report,goal="",constraints=None):
        constraints=list(constraints or [])
        models=self.model_builder.build_options(idea,constraints)
        scored=[{"model":m,"strategy_score":build_strategy_score(idea,m,market_report,constraints)} for m in models]
        strategy=select_strategy(scored)
        positioning=build_positioning(idea,market_report)
        risk_map=build_risk_map(idea,constraints)
        selected=strategy.get("recommended_model") or (models[0] if models else {})
        selected_name=selected.get("name", "selected")
        validation_model=("Service-led" if "Service" in selected_name or "Hybrid" in selected_name else "Prototype-led")
        long_term_model=selected_name
        candidate_title = idea.get("title") or idea.get("opportunity",{}).get("title") or idea.get("idea") or "the selected opportunity"
        mvp_plan=self.mvp.build(idea,selected,constraints)
        strategy["recommended_opportunity"] = candidate_title
        strategy["validation_model"] = validation_model
        strategy["long_term_product_model"] = long_term_model
        strategy["recommendation_reason"] = f"Start with the {validation_model.lower()} validation approach for {candidate_title}; keep the {long_term_model} model as the current long-term product direction."
        plan_90=build_90_day_plan(strategy,idea,constraints)
        idea_handoff = _build_idea_handoff(idea)
        idea_handoff_qa = validate_semantic_handoff(idea_handoff, contract="idea_to_strategy_v1")
        output={
            "status":"DRAFT","engine_id":"E-04","engine_version":"O13-v1.1-O41",
            "goal":goal,"idea":idea_handoff,"idea_handoff":idea_handoff,"idea_handoff_qa":idea_handoff_qa,
            "business_model_options":models,"scored_models":scored,
            "positioning":positioning,"risk_map":risk_map,"mvp_plan":mvp_plan,
            "strategy":strategy,"90_day_plan":plan_90,
        }
        product_handoff = build_strategy_to_product_handoff(output)
        handoff_qa = validate_semantic_handoff(product_handoff, contract="strategy_to_product_v1")
        output["product_handoff"] = product_handoff
        output["handoff_qa"] = handoff_qa
        if idea_handoff_qa["status"] != "PASS":
            output["status"] = "FAILED"
            output["failed_stage"] = "idea_to_strategy_handoff_validation"
            return output
        if handoff_qa["status"] != "PASS":
            output["status"] = "FAILED"
            output["failed_stage"] = "strategy_to_product_handoff_validation"
            return output
        qa=validate_strategy_output(output)
        output["qa"]=qa
        output["status"]="COMPLETE" if qa["status"]=="PASS" else "FAILED"
        return output
