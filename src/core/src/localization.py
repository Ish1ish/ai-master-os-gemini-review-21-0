from __future__ import annotations
from typing import Any, Dict, List


def _ar_model(model: str) -> str:
    return {
        "Service / Productized Service": "خدمة مُمنتجة",
        "Digital Product": "منتج رقمي",
        "Hybrid Product + Service": "منتج + خدمة",
        "Productized Service": "خدمة مُمنتجة",
    }.get(str(model or ""), str(model or "غير محدد"))


def _top_idea(result: Dict[str, Any]) -> Dict[str, Any]:
    ideas=result.get("ideas") or {}
    ranked=(ideas.get("scores") or {}).get("ranked_ideas") or []
    if ranked:
        return ranked[0]
    raw=ideas.get("ideas") or []
    return raw[0] if raw else {}


def _normalize_model_name(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().replace("-", " ").split())


def _numeric_score(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _opportunity_score(result: Dict[str, Any], top: Dict[str, Any]) -> Any:
    candidates = [
        top.get("opportunity_score"),
        (top.get("opportunity") or {}).get("opportunity_score"),
    ]
    idea_id = top.get("idea_id")
    opportunity_id = top.get("opportunity_id") or (top.get("opportunity") or {}).get("opportunity_id")
    ideas = result.get("ideas") or {}
    for candidate in ideas.get("opportunity_candidates") or []:
        if idea_id and candidate.get("idea_id") == idea_id:
            candidates.append(candidate.get("opportunity_score"))
        if opportunity_id and candidate.get("opportunity_id") == opportunity_id:
            candidates.append(candidate.get("opportunity_score"))
    for value in candidates:
        score = _numeric_score(value)
        if score is not None:
            return int(score) if isinstance(score, float) and score.is_integer() else score
    return None


def _strategy_score(result: Dict[str, Any], selected: Dict[str, Any], selected_name: str) -> Any:
    strategy=result.get("strategy") or {}
    rows=strategy.get("scored_models") or []
    selected_id=str(selected.get("model_id") or "").strip()
    selected_norm=_normalize_model_name(selected_name)
    for row in rows:
        model=(row.get("model") or {})
        model_name=_normalize_model_name(model.get("name"))
        model_id=str(model.get("model_id") or "").strip()
        if (selected_id and model_id == selected_id) or (selected_norm and model_name == selected_norm):
            score=_numeric_score((row.get("strategy_score") or {}).get("overall_score"))
            if score is not None:
                return int(score) if isinstance(score, float) and score.is_integer() else score
    # Preserve the engine's ranked decision when the selected model is represented
    # with a slightly different display name downstream.
    ranked=strategy.get("ranked_models") or []
    if ranked:
        score=_numeric_score(((ranked[0].get("strategy_score") or {}).get("overall_score")))
        if score is not None:
            return int(score) if isinstance(score, float) and score.is_integer() else score
    return None

def _validation_experiment(result: Dict[str, Any]) -> Dict[str, Any]:
    ideas=result.get("ideas") or {}
    plans=(ideas.get("validation") or {}).get("idea_validation_plans") or []
    if not plans:
        return {}
    return plans[0].get("validation_experiment") or {}


def _evidence_surface(result: Dict[str, Any]) -> Dict[str, Any]:
    market=result.get("market") or {}
    report=market.get("report") or {}
    return {
        "boundary": report.get("evidence_boundary") or "unknown",
        "source_count": report.get("source_count", 0),
        "evidence_count": report.get("evidence_count", 0),
        "local_source_count": report.get("local_source_count", 0),
        "local_evidence_count": report.get("local_evidence_count", 0),
        "regional_evidence_count": report.get("regional_evidence_count", 0),
    }

def build_decision_surface(result: Dict[str, Any]) -> Dict[str, Any]:
    top=_top_idea(result)
    strategy=result.get("strategy") or {}
    sblock=strategy.get("strategy") or {}
    product=result.get("product") or {}
    definition=product.get("product_definition") or {}
    evidence=_evidence_surface(result)
    selected=(sblock.get("recommended_model") or {})
    selected_name=selected.get("name") or definition.get("product_type") or "Focused Business Solution"
    validation_model=strategy.get("validation_model") or ("Service-led" if "Service" in str(selected_name) or "Hybrid" in str(selected_name) else "Prototype-led")
    long_term_model=strategy.get("long_term_product_model") or selected_name
    experiment=_validation_experiment(result)
    score=_opportunity_score(result, top)
    confidence=top.get("confidence") or "medium"
    boundary=evidence["boundary"]
    return {
        "recommendation": top.get("title") or definition.get("product_name_placeholder") or "الفرصة المختارة",
        "customer": top.get("customer_segment") or definition.get("target_audience") or "الجمهور المستهدف غير محدد بعد",
        "problem": top.get("problem_statement") or definition.get("core_problem") or "المشكلة غير محددة بعد",
        "desired_outcome": top.get("desired_outcome") or definition.get("core_promise") or "النتيجة المطلوبة غير محددة بعد",
        "validation_model": validation_model,
        "long_term_product_model": long_term_model,
        "mvp_direction": (product.get("mvp_plan") or strategy.get("mvp_plan") or {}).get("scope") or [],
        "opportunity_score": score,
        "strategy_score": _strategy_score(result, selected, selected_name),
        "confidence": confidence,
        "confidence_basis": "Derived from the strongest ranked idea plus the market evidence boundary; it does not represent probability of success.",
        "evidence_boundary": boundary,
        "evidence": evidence,
        "validation_experiment": experiment,
        "next_action": experiment.get("method") or "Validate the recommended opportunity before committing capital or external actions.",
        "go_decision_rule": experiment.get("decision_rule") or "Run the test, collect evidence, then decide GO / REFINE / NO-GO.",
        "status": "HYPOTHESIS",
    }

def build_arabic_decision_summary(result: Dict[str, Any]) -> Dict[str, Any]:
    surface=build_decision_surface(result)
    strategy=result.get("strategy") or {}
    model=surface["long_term_product_model"]
    exp=surface["validation_experiment"] or {}
    evidence=surface["evidence"]
    boundary=surface["evidence_boundary"]
    if boundary=="local_evidence_supported":
        local_evidence=(f"الدليل المحلي مدعوم: {evidence['local_source_count']} مصادر محلية و{evidence['local_evidence_count']} عناصر دليل محلية من إجمالي {evidence['source_count']} مصدر و{evidence['evidence_count']} دليل.")
    else:
        local_evidence=(f"حدود الدليل: {evidence['local_source_count']} مصادر محلية و{evidence['local_evidence_count']} عناصر دليل؛ لا يكفي ذلك وحده لإثبات السوق المصري على نطاق واسع.")
    validation_text=exp.get("method") or "نفّذ اختبارًا ميدانيًا قابلًا للقياس قبل البناء."
    threshold_text=""
    if exp.get("success_threshold"):
        threshold_text=" | ".join(str(v) for v in exp["success_threshold"].values())
    return {
        "language":"ar",
        "title":"ملخص القرار بالعربية",
        "recommendation":surface["recommendation"],
        "recommended_model":_ar_model(model),
        "validation_model":"تحقق بالخدمة" if surface["validation_model"]=="Service-led" else "تحقق بنموذج أولي",
        "long_term_product_model":_ar_model(model),
        "product_type":surface["long_term_product_model"],
        "customer_segment":surface["customer"],
        "problem":surface["problem"],
        "desired_outcome":surface["desired_outcome"],
        "mvp":surface["mvp_direction"][:6],
        "validation":exp,
        "validation_experiment":validation_text,
        "success_threshold":threshold_text,
        "opportunity_score":surface["opportunity_score"],
        "strategy_score":surface["strategy_score"],
        "confidence":surface["confidence"],
        "confidence_basis":"الثقة وصف لقوة الدليل الحالي وليست احتمال نجاح.",
        "evidence_boundary":boundary,
        "evidence":evidence,
        "local_evidence":local_evidence,
        "next_action":validation_text,
        "go_decision_rule":surface["go_decision_rule"],
        "why":strategy.get("recommendation_reason") or "الاختيار مبني على سرعة التعلم وتوافق الموارد وقابلية التحقق.",
        "governance":"هناك بوابة موافقة بشرية قبل أي نشر أو أثر خارجي.",
        "how_to_read":[
            "الفرصة المقترحة فرضية عمل وليست حقيقة مثبتة.",
            "Opportunity Score يحدد أولوية الاختبار، وليس احتمال النجاح.",
            "Validation Model يوضح كيف نختبر الآن، وLong-term Product Model يوضح اتجاه المنتج لاحقًا.",
            "نفّذ تجربة واحدة، قِس العتبة المحددة، ثم اتخذ GO / REFINE / NO-GO.",
        ],
    }
