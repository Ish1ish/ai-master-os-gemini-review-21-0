"""Deterministic context views for engine-to-engine runtime boundaries.

The runtime may retain full engine outputs for traceability, but downstream engines
receive purpose-built, minimal context views instead of upstream raw payloads.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable

from .handoff_contracts import compact_semantic_text, normalize_source_refs


def _refs(value: Dict[str, Any] | None) -> list[str]:
    if not isinstance(value, dict):
        return []
    return normalize_source_refs(value.get("source_refs"))


def market_context_for_strategy(market_report: Dict[str, Any], idea_handoff: Dict[str, Any]) -> Dict[str, Any]:
    findings = []
    for f in (market_report.get("findings") or [])[:12]:
        if not isinstance(f, dict):
            continue
        sid = str(f.get("source_id") or "").strip()
        statement = compact_semantic_text(f.get("statement") or f.get("snippet") or f.get("content"))
        if sid and statement:
            findings.append({"source_id": sid, "statement": statement})
    return {
        "source_count": len(findings),
        "findings": findings,
        "themes": [
            {"theme_id": str(t.get("theme_id")), "statement": compact_semantic_text(t.get("statement")), "source_id": str(t.get("source_id"))}
            for t in (market_report.get("themes") or [])[:12]
            if isinstance(t, dict)
        ],
        "idea_handoff": {
            "object_id": idea_handoff.get("object_id", ""),
            "idea": compact_semantic_text(idea_handoff.get("idea")),
            "evidence_summary": compact_semantic_text(idea_handoff.get("evidence_summary")),
            "source_refs": _refs(idea_handoff),
            "confidence": idea_handoff.get("confidence", "medium"),
        },
    }


def strategy_context_for_product(strategy: Dict[str, Any], strategy_handoff: Dict[str, Any]) -> Dict[str, Any]:
    core = strategy.get("strategy") or {}
    positioning = strategy.get("positioning") or {}
    return {
        "idea": {
            "idea_id": strategy_handoff.get("object_id", ""),
            "idea": compact_semantic_text(strategy_handoff.get("problem") or strategy_handoff.get("idea")),
            "source_refs": _refs(strategy_handoff),
            "status": "HYPOTHESIS",
        },
        "strategy": {
            "recommended_model": core.get("recommended_model") or {},
            "recommendation_reason": compact_semantic_text(core.get("recommendation_reason") or strategy.get("recommendation_reason")),
            "validation_model": core.get("validation_model"),
            "long_term_product_model": core.get("long_term_product_model"),
            "positioning": {
                "target_problem": compact_semantic_text(positioning.get("target_problem")),
                "promise": compact_semantic_text(positioning.get("promise")),
            },
        },
        "product_handoff": strategy_handoff,
    }


def product_context_for_brand(product: Dict[str, Any], product_handoff: Dict[str, Any]) -> Dict[str, Any]:
    definition = dict(product.get("product_definition") or {})
    return {
        "product_definition": {
            "core_problem": compact_semantic_text(product_handoff.get("problem") or definition.get("core_problem")),
            "core_promise": compact_semantic_text(product_handoff.get("promise") or definition.get("core_promise")),
            "target_audience": compact_semantic_text(product_handoff.get("audience") or definition.get("target_audience")),
            "product_type": compact_semantic_text(definition.get("product_type")),
        },
        "strategy": {
            "recommendation_reason": compact_semantic_text((product.get("strategy") or {}).get("recommendation_reason")),
        },
        "product_to_brand_handoff": product_handoff,
    }


def brand_context_for_content(brand: Dict[str, Any], brand_handoff: Dict[str, Any], product_handoff: Dict[str, Any]) -> Dict[str, Any]:
    dna = dict(brand.get("brand_dna") or {})
    voice = dict(brand.get("voice") or {})
    return {
        "brand_dna": {
            "audience": compact_semantic_text(brand_handoff.get("audience") or dna.get("audience")),
            "personality": dna.get("personality", [])[:6] if isinstance(dna.get("personality"), list) else [compact_semantic_text(dna.get("personality"))],
            "problem_space": compact_semantic_text(dna.get("problem_space") or product_handoff.get("problem")),
        },
        "voice": voice,
        "brand_to_content_handoff": brand_handoff,
    }


def content_context_for_visual(content: Dict[str, Any], content_handoff: Dict[str, Any], brand_handoff: Dict[str, Any]) -> Dict[str, Any]:
    topics = ((content.get("topics") or {}).get("topics") or [])
    t = topics[0] if topics and isinstance(topics[0], dict) else {}
    return {
        "topic_id": t.get("topic_id") or content_handoff.get("object_id"),
        "pillar": compact_semantic_text(t.get("pillar")),
        "topic": compact_semantic_text(content_handoff.get("topic") or t.get("topic") or t.get("title")),
        "objective": compact_semantic_text(content_handoff.get("objective") or t.get("objective")),
        "platform": content_handoff.get("platform", "Instagram"),
        "content_to_visual_handoff": content_handoff,
        "brand_context": {
            "audience": compact_semantic_text(brand_handoff.get("audience")),
            "message": compact_semantic_text(brand_handoff.get("message")),
        },
    }


def visual_context_for_marketing(visual: Dict[str, Any], visual_handoff: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "visual_to_marketing_handoff": visual_handoff,
        "visual_brief": {
            "concept": compact_semantic_text((visual.get("visual_brief") or {}).get("concept")),
            "objective": compact_semantic_text((visual.get("visual_brief") or {}).get("objective")),
            "platform": compact_semantic_text((visual.get("visual_brief") or {}).get("platform") or visual_handoff.get("platform")),
        },
    }


def marketing_context_for_sales(marketing: Dict[str, Any], marketing_handoff: Dict[str, Any]) -> Dict[str, Any]:
    offer = dict(marketing.get("offer") or {})
    audience = dict(marketing.get("audience") or {})
    return {
        "offer": {
            "offer_name": compact_semantic_text(offer.get("offer_name")),
            "core_promise": compact_semantic_text(marketing_handoff.get("offer_summary") or offer.get("core_promise")),
            "mechanism": compact_semantic_text(offer.get("mechanism")),
        },
        "audience": {
            "primary_segment": compact_semantic_text(marketing_handoff.get("audience") or audience.get("primary_segment")),
            "problem": compact_semantic_text(audience.get("problem")),
            "desired_outcome": compact_semantic_text(audience.get("desired_outcome")),
        },
        "marketing_to_sales_handoff": marketing_handoff,
    }


def sales_context_for_automation(sales_handoff: Dict[str, Any]) -> Dict[str, Any]:
    return {"sales_to_automation_handoff": sales_handoff}


def automation_context_for_analytics(automation_handoff: Dict[str, Any]) -> Dict[str, Any]:
    return {"automation_to_analytics_handoff": automation_handoff}
