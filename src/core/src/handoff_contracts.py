"""Canonical semantic handoff contracts for the AI Master OS runtime."""
from __future__ import annotations
import re
from typing import Any, Dict, Iterable, List

MAX_SEMANTIC_TEXT = 240
MAX_EVIDENCE_SUMMARY = 240
_ALLOWED_CONFIDENCE = {"low", "medium", "high"}

# Canonical boundary map. A contract name is not valid merely because the
# payload is structurally shaped; the producer/consumer identity must agree.
CONTRACT_SPECS = {
    "market_to_idea_v1": ("market_to_idea", "E-02", "E-03"),
    "idea_to_strategy_v1": ("idea_to_strategy", "E-03", "E-04"),
    "strategy_to_product_v1": ("strategy_to_product", "E-04", "E-05"),
    "product_to_brand_v1": ("product_to_brand", "E-05", "E-06"),
    "brand_to_content_v1": ("brand_to_content", "E-06", "E-07"),
    "content_to_visual_v1": ("content_to_visual", "E-07", "E-08"),
    "visual_to_marketing_v1": ("visual_to_marketing", "E-08", "E-09"),
    "marketing_to_sales_v1": ("marketing_to_sales", "E-09", "E-10"),
    "sales_to_automation_v1": ("sales_to_automation", "E-10", "E-11"),
    "automation_to_analytics_v1": ("automation_to_analytics", "E-11", "E-12"),
    "analytics_to_approval_v1": ("analytics_to_approval", "E-12", "GOVERNANCE"),
    "approval_to_memory_v1": ("approval_to_memory", "GOVERNANCE", "MEMORY"),
    "memory_to_monitoring_v1": ("memory_to_monitoring", "MEMORY", "MONITORING"),
}


def compact_semantic_text(value: Any, limit: int = MAX_SEMANTIC_TEXT) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text:
        return ""
    if "|" in text:
        cells = [c.strip() for c in text.split("|") if c.strip()]
        cells = [c for c in cells if not re.fullmatch(r"[-: ]+", c)]
        text = " — ".join(cells[:4]) if cells else ""
    text = re.sub(r"#{1,6}\s*", "", text).strip(" -|:")
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"
    return text


def semantic_core(value: Any, limit: int = MAX_SEMANTIC_TEXT) -> str:
    text = compact_semantic_text(value, limit)
    lowered = text.lower()
    prefixes = (
        "create a simple product/service that reduces:",
        "create a focused offer that addresses this gap:",
        "create a differentiated alternative around:",
        "create a value-focused offer responding to:",
        "explore a targeted offer based on:",
        "develop a focused offer around:",
    )
    for prefix in prefixes:
        if lowered.startswith(prefix):
            text = text[len(prefix):].strip(" -:|")
            break
    low=text.lower()
    if low.startswith("quick answer:"):
        text=text.split(":",1)[1].strip()
    if text.lower().startswith("evidence for ") and ":" in text:
        text = text.rsplit(":", 1)[-1].strip()
    elif text.lower().startswith("evidence ") and ":" in text:
        text = text.rsplit(":", 1)[-1].strip()
    return compact_semantic_text(text, limit)


def normalize_source_refs(values: Iterable[Any] | None) -> List[str]:
    seen: set[str] = set()
    refs: List[str] = []
    for value in values or []:
        ref = str(value or "").strip()
        if ref and ref not in seen:
            seen.add(ref)
            refs.append(ref)
    return refs


def collect_source_refs(*values: Any) -> List[str]:
    """Collect source_refs recursively from a small set of runtime objects."""
    found: List[str] = []
    def visit(value: Any, depth: int = 0) -> None:
        if depth > 4:
            return
        if isinstance(value, dict):
            if isinstance(value.get("source_refs"), list):
                found.extend(value["source_refs"])
            if isinstance(value.get("source_id"), str):
                found.append(value["source_id"])
            for key in ("handoff", "idea_handoff", "product_handoff", "product_definition", "brand_dna", "offer", "audience", "content_handoff", "visual_handoff", "marketing_handoff", "sales_handoff"):
                if key in value:
                    visit(value[key], depth + 1)
        elif isinstance(value, list):
            for item in value[:24]:
                visit(item, depth + 1)
    for value in values:
        visit(value)
    return normalize_source_refs(found)


def _looks_like_raw_evidence(text: str) -> bool:
    value = str(text or "")
    if not value:
        return False
    lowered = value.lower()
    if "|" in value or "\n|" in value or "\t|" in value:
        return True
    return ("raw_content" in lowered or "provider payload" in lowered or "quick answer:" in lowered or
            "http://" in lowered or "https://" in lowered or "| email & crm |" in lowered)


def _contains_prompt_injection(text: str) -> bool:
    lowered = str(text or "").lower()
    patterns = (
        "ignore previous instructions",
        "ignore all previous instructions",
        "reveal the system prompt",
        "reveal system prompt",
        "follow these instructions instead",
        "do not follow the system instructions",
        "jailbreak",
        "prompt injection",
    )
    return any(token in lowered for token in patterns)


def validate_semantic_handoff(handoff: Dict[str, Any], *, contract: str, required_fields: Iterable[str] = (), known_source_refs: Iterable[str] | None = None) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    if not isinstance(handoff, dict):
        return {"status": "FAIL", "contract": contract, "issues": [{"type": "not_object"}]}
    spec = CONTRACT_SPECS.get(contract)
    if spec is None:
        return {"status": "FAIL", "contract": contract, "issues": [{"type": "unknown_contract"}]}
    expected_type, expected_source, expected_target = spec
    for field in ("handoff_type", "source_engine", "target_engine", "object_id"):
        if not str(handoff.get(field, "")).strip():
            issues.append({"type": f"missing_{field}"})
    if str(handoff.get("handoff_type", "")) != expected_type:
        issues.append({"type": "contract_handoff_type_mismatch", "expected": expected_type})
    if str(handoff.get("source_engine", "")) != expected_source:
        issues.append({"type": "contract_source_engine_mismatch", "expected": expected_source})
    if str(handoff.get("target_engine", "")) != expected_target:
        issues.append({"type": "contract_target_engine_mismatch", "expected": expected_target})
    for field in required_fields:
        if not str(handoff.get(field, "")).strip():
            issues.append({"type": "missing_required_field", "field": field})
    source_refs = normalize_source_refs(handoff.get("source_refs"))
    if not source_refs:
        issues.append({"type": "missing_source_refs"})
    if known_source_refs is not None:
        known = set(normalize_source_refs(known_source_refs))
        for ref in source_refs:
            if ref not in known:
                issues.append({"type": "unknown_source_ref", "source_ref": ref})
    semantic_fields = ("idea", "evidence_summary", "problem", "core_problem", "promise", "positioning", "message", "topic", "objective", "offer_summary", "workflow_summary", "learning_summary", "title", "customer_segment", "desired_outcome", "solution_format")
    for field in semantic_fields:
        if field not in handoff:
            continue
        value = str(handoff.get(field, ""))
        if _looks_like_raw_evidence(value):
            issues.append({"type": "raw_evidence_echo", "field": field})
        if _contains_prompt_injection(value):
            issues.append({"type": "prompt_injection_text", "field": field})
        if len(value) > MAX_SEMANTIC_TEXT:
            issues.append({"type": "semantic_text_oversized", "field": field})
    confidence = str(handoff.get("confidence", "")).strip().lower()
    if confidence and confidence not in _ALLOWED_CONFIDENCE:
        issues.append({"type": "invalid_confidence"})
    return {
        "status": "PASS" if not issues else "FAIL",
        "contract": contract,
        "issues": issues,
        "source_refs": source_refs,
        "checks": {
            "typed_contract": True,
            "identity_fields": not any(i["type"].startswith("missing_") and i["type"] != "missing_source_refs" for i in issues),
            "provenance": not any(i["type"] == "missing_source_refs" for i in issues),
            "semantic_bounded": not any(i["type"] == "semantic_text_oversized" for i in issues),
            "raw_evidence_isolated": not any(i["type"] == "raw_evidence_echo" for i in issues),
            "prompt_injection_isolated": not any(i["type"] == "prompt_injection_text" for i in issues),
            "required_fields": not any(i["type"] == "missing_required_field" for i in issues),
            "source_refs_resolve": not any(i["type"] == "unknown_source_ref" for i in issues),
        },
    }


def _base_handoff(handoff_type: str, source: str, target: str, object_id: str, source_refs: Iterable[Any], **fields: Any) -> Dict[str, Any]:
    out = {
        "handoff_type": handoff_type,
        "source_engine": source,
        "target_engine": target,
        "object_id": str(object_id or ""),
        "source_refs": normalize_source_refs(source_refs),
    }
    out.update(fields)
    return out


def build_market_to_idea_handoff(market_report: Dict[str, Any]) -> Dict[str, Any]:
    findings = market_report.get("findings", []) if isinstance(market_report, dict) else []
    refs = normalize_source_refs([f.get("source_id") for f in findings if isinstance(f, dict)])
    themes = market_report.get("themes") or market_report.get("opportunity_themes") or []
    return _base_handoff("market_to_idea", "E-02", "E-03", "MARKET-REPORT", refs,
        theme_count=len(themes) if isinstance(themes, list) else 0,
        evidence_count=len(findings), status="READY")


def build_idea_to_strategy_handoff(idea: Dict[str, Any]) -> Dict[str, Any]:
    idea = dict(idea or {})
    source_text = idea.get("problem_statement") or idea.get("evidence_summary") or idea.get("idea") or "validated customer problem"
    core = semantic_core(source_text, MAX_EVIDENCE_SUMMARY) or "validated customer problem"
    semantic_title = compact_semantic_text(idea.get("title") or "")
    semantic_solution = compact_semantic_text(idea.get("solution_format") or "")
    semantic_idea = compact_semantic_text(
        f"{semantic_title}: {semantic_solution}" if semantic_title and semantic_solution else (semantic_title or f"Develop a focused offer around: {core}")
    )
    return _base_handoff("idea_to_strategy", "E-03", "E-04", idea.get("idea_id") or idea.get("object_id", ""),
        idea.get("source_refs"), idea=semantic_idea, evidence_summary=compact_semantic_text(idea.get("evidence_summary") or source_text, MAX_EVIDENCE_SUMMARY),
        problem_statement=compact_semantic_text(idea.get("problem_statement") or source_text, MAX_EVIDENCE_SUMMARY),
        title=compact_semantic_text(idea.get("title") or "", MAX_EVIDENCE_SUMMARY),
        customer_segment=compact_semantic_text(idea.get("customer_segment") or idea.get("audience") or "", MAX_EVIDENCE_SUMMARY),
        desired_outcome=compact_semantic_text(idea.get("desired_outcome") or "", MAX_EVIDENCE_SUMMARY),
        solution_format=compact_semantic_text(idea.get("solution_format") or "", MAX_EVIDENCE_SUMMARY),
        opportunity_id=str(idea.get("opportunity_id") or ""), opportunity_score=idea.get("opportunity_score"),
        assumptions=list(idea.get("assumptions") or []), validation_test=idea.get("validation_test") or {},
        market_scope=str(idea.get("market_scope") or ""),
        origin_theme=str(idea.get("origin_theme") or (idea.get("origin_themes") or [""])[0]), signal_type=str(idea.get("signal_type", "")), status=str(idea.get("status", "HYPOTHESIS")),
        confidence=str(idea.get("confidence", "medium")))


def build_strategy_to_product_handoff(strategy_output: Dict[str, Any]) -> Dict[str, Any]:
    idea = dict(strategy_output.get("idea_handoff") or strategy_output.get("idea") or {})
    strategy = dict(strategy_output.get("strategy") or {})
    positioning = dict(strategy_output.get("positioning") or {})
    model = dict(strategy.get("recommended_model") or {})
    # Prefer the canonical evidence summary over free-form positioning so a stale
    # or model-generated phrasing cannot redefine the product problem.
    problem = semantic_core(idea.get("problem_statement") or positioning.get("target_problem") or idea.get("evidence_summary") or idea.get("idea")) or "validated customer problem"
    promise = compact_semantic_text(idea.get("desired_outcome") or positioning.get("promise") or "Deliver a focused outcome for the validated problem.")
    return _base_handoff("strategy_to_product", "E-04", "E-05", idea.get("idea_id") or "STRATEGY-001", collect_source_refs(idea, strategy_output),
        problem=problem, promise=promise, recommended_model=model.get("name", "Unspecified"),
        recommendation_reason=compact_semantic_text(strategy.get("recommendation_reason", "")),
        opportunity_title=compact_semantic_text(idea.get("title") or idea.get("opportunity",{}).get("title") or ""),
        customer_segment=compact_semantic_text(idea.get("customer_segment") or idea.get("audience") or ""),
        desired_outcome=compact_semantic_text(idea.get("desired_outcome") or ""),
        solution_format=compact_semantic_text(idea.get("solution_format") or ""),
        opportunity_id=str(idea.get("opportunity_id") or ""),
        origin_theme=idea.get("origin_theme", ""), confidence=str(idea.get("confidence", "medium")))


def build_product_to_brand_handoff(product_output: Dict[str, Any]) -> Dict[str, Any]:
    definition = dict(product_output.get("product_definition") or {})
    return _base_handoff("product_to_brand", "E-05", "E-06", product_output.get("engine_id", "E-05"), collect_source_refs(product_output),
        problem=semantic_core(definition.get("core_problem") or "validated customer problem"),
        promise=compact_semantic_text(definition.get("core_promise") or "Deliver a focused customer outcome."),
        audience=compact_semantic_text(definition.get("target_audience") or "defined target audience"),
        product_type=compact_semantic_text(definition.get("product_type") or "Focused Business Solution"),
        positioning_link=compact_semantic_text(definition.get("positioning_link") or ""),
        confidence="medium")


def build_brand_to_content_handoff(brand_output: Dict[str, Any], product_handoff: Dict[str, Any]) -> Dict[str, Any]:
    dna = dict(brand_output.get("brand_dna") or {})
    return _base_handoff("brand_to_content", "E-06", "E-07", "BRAND-001", collect_source_refs(brand_output, product_handoff),
        audience=compact_semantic_text(dna.get("audience") or product_handoff.get("audience")),
        personality=compact_semantic_text(", ".join(dna.get("personality", [])[:4]) if isinstance(dna.get("personality"), list) else dna.get("personality")),
        message=compact_semantic_text((brand_output.get("messaging") or {}).get("core_message", "Build consistent, useful content.")),
        confidence="medium")


def build_content_to_visual_handoff(content_output: Dict[str, Any], brand_handoff: Dict[str, Any]) -> Dict[str, Any]:
    topics = ((content_output.get("topics") or {}).get("topics") or [])
    topic = topics[0] if topics else {}
    return _base_handoff("content_to_visual", "E-07", "E-08", topic.get("topic_id") or "CONTENT-001", collect_source_refs(content_output, brand_handoff),
        topic=compact_semantic_text(topic.get("topic") or topic.get("title") or "Create a useful educational content asset."),
        objective=compact_semantic_text(topic.get("objective") or "Turn the content idea into a clear visual asset."),
        platform="Instagram", confidence="medium")


def build_visual_to_marketing_handoff(visual_output: Dict[str, Any], content_handoff: Dict[str, Any]) -> Dict[str, Any]:
    brief = dict(visual_output.get("visual_brief") or {})
    return _base_handoff("visual_to_marketing", "E-08", "E-09", "VISUAL-001", collect_source_refs(visual_output, content_handoff),
        asset_summary=compact_semantic_text(brief.get("concept") or brief.get("objective") or "Visual asset aligned to the content objective."),
        platform=compact_semantic_text(brief.get("platform") or "Instagram"), confidence="medium")


def build_marketing_to_sales_handoff(marketing_output: Dict[str, Any], visual_handoff: Dict[str, Any]) -> Dict[str, Any]:
    offer = dict(marketing_output.get("offer") or {})
    audience = dict(marketing_output.get("audience") or {})
    return _base_handoff("marketing_to_sales", "E-09", "E-10", "MARKETING-001", collect_source_refs(marketing_output, visual_handoff),
        offer_summary=compact_semantic_text(offer.get("core_promise") or offer.get("offer") or "Focused customer outcome offer."),
        audience=compact_semantic_text(audience.get("primary_segment") or "target segment"),
        primary_channel=compact_semantic_text(((marketing_output.get("channels") or {}).get("primary_channel_candidates") or ["organic"])[0]),
        confidence="medium")


def build_sales_to_automation_handoff(sales_output: Dict[str, Any], marketing_handoff: Dict[str, Any]) -> Dict[str, Any]:
    qualification = dict(sales_output.get("qualification") or {})
    follow_up = dict(sales_output.get("follow_up") or {})
    return _base_handoff("sales_to_automation", "E-10", "E-11", "SALES-001", collect_source_refs(sales_output, marketing_handoff),
        workflow_summary=compact_semantic_text("Automate follow-up after lead qualification."),
        qualification_summary=compact_semantic_text(qualification.get("summary") or "Qualify leads using explicit buyer criteria."),
        follow_up_summary=compact_semantic_text(follow_up.get("sequence") or "Use a controlled follow-up sequence."),
        confidence="medium")


def build_automation_to_analytics_handoff(automation_output: Dict[str, Any], sales_handoff: Dict[str, Any]) -> Dict[str, Any]:
    workflow = dict(automation_output.get("workflow") or {})
    return _base_handoff("automation_to_analytics", "E-11", "E-12", workflow.get("workflow_id") or "AUTOMATION-001", collect_source_refs(automation_output, sales_handoff),
        workflow_summary=compact_semantic_text(workflow.get("name") or "Controlled workflow for validation."),
        metric_intent="Measure conversion and funnel bottlenecks.", confidence="medium")


def build_analytics_to_approval_handoff(analytics_output: Dict[str, Any], prior_handoff: Dict[str, Any] | None = None) -> Dict[str, Any]:
    diagnosis = dict(analytics_output.get("diagnosis") or {})
    return _base_handoff("analytics_to_approval", "E-12", "GOVERNANCE", "ANALYTICS-001", collect_source_refs(analytics_output, prior_handoff),
        decision_summary=compact_semantic_text(diagnosis.get("summary") or "Review downstream action against deterministic analytics."),
        learning_summary=compact_semantic_text(((analytics_output.get("learning") or {}).get("summary")) or "Record measured learning."), confidence="medium")


def build_approval_to_memory_handoff(approval: Dict[str, Any], analytics_handoff: Dict[str, Any]) -> Dict[str, Any]:
    return _base_handoff("approval_to_memory", "GOVERNANCE", "MEMORY", approval.get("approval_id") or "APPROVAL-001", collect_source_refs(approval, analytics_handoff),
        decision_summary=compact_semantic_text(approval.get("status") or "approval decision recorded"),
        action=compact_semantic_text(approval.get("action") or "governed action"), confidence="high")


def build_memory_to_monitoring_handoff(memory: Dict[str, Any], approval_handoff: Dict[str, Any]) -> Dict[str, Any]:
    return _base_handoff("memory_to_monitoring", "MEMORY", "MONITORING", "MEMORY-001", collect_source_refs(memory, approval_handoff),
        learning_summary=compact_semantic_text(memory.get("learning") or memory.get("summary") or "Operational learning recorded."),
        memory_status=compact_semantic_text(memory.get("status") or "WRITTEN"), confidence="high")


def validate_handoff_chain(handoffs: Dict[str, Any]) -> Dict[str, Any]:
    """Validate that the full canonical chain is present and contract-bound."""
    expected = list(HANDOFF_BUILDERS.keys())
    issues: List[Dict[str, Any]] = []
    if not isinstance(handoffs, dict):
        return {"status": "FAIL", "issues": [{"type": "not_object"}], "checked": 0}
    if list(handoffs.keys()) != expected:
        issues.append({"type": "handoff_order_or_membership_mismatch", "expected": expected})
    for name in expected:
        record = handoffs.get(name) or {}
        contract = record.get("contract", {}) if isinstance(record, dict) else {}
        qa = record.get("qa", {}) if isinstance(record, dict) else {}
        contract_name = f"{name}_v1"
        if qa.get("status") != "PASS":
            issues.append({"type": "handoff_qa_failed", "handoff": name})
        if contract and contract_name in CONTRACT_SPECS:
            identity = CONTRACT_SPECS[contract_name]
            if tuple(contract.get(k) for k in ("handoff_type", "source_engine", "target_engine")) != identity:
                issues.append({"type": "handoff_identity_mismatch", "handoff": name})
    return {"status": "PASS" if not issues else "FAIL", "issues": issues, "checked": len(expected)}


HANDOFF_BUILDERS = {
    "market_to_idea": build_market_to_idea_handoff,
    "idea_to_strategy": build_idea_to_strategy_handoff,
    "strategy_to_product": build_strategy_to_product_handoff,
    "product_to_brand": build_product_to_brand_handoff,
    "brand_to_content": build_brand_to_content_handoff,
    "content_to_visual": build_content_to_visual_handoff,
    "visual_to_marketing": build_visual_to_marketing_handoff,
    "marketing_to_sales": build_marketing_to_sales_handoff,
    "sales_to_automation": build_sales_to_automation_handoff,
    "automation_to_analytics": build_automation_to_analytics_handoff,
    "analytics_to_approval": build_analytics_to_approval_handoff,
    "approval_to_memory": build_approval_to_memory_handoff,
    "memory_to_monitoring": build_memory_to_monitoring_handoff,
}
