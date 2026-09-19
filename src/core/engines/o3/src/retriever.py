from typing import Dict, List, Any
from .knowledge_store import KnowledgeStore
from .models import KnowledgeItem


ENGINE_TERMS = {
    "E-01": ["prompt", "task", "context", "format", "examples", "constraints"],
    "E-02": ["market", "customer", "competitor", "demand", "niche", "evidence"],
    "E-03": ["idea", "concept", "angle", "hypothesis", "validate"],
    "E-04": ["strategy", "business", "model", "niche", "offer", "roadmap"],
    "E-05": ["product", "ebook", "guide", "mvp", "structure"],
    "E-06": ["brand", "positioning", "voice", "identity", "logo"],
    "E-07": ["content", "social", "hook", "caption", "repurpose"],
    "E-08": ["visual", "design", "mockup", "banner", "ui"],
    "E-09": ["marketing", "funnel", "campaign", "ads", "email", "cro"],
    "E-10": ["sales", "listing", "pricing", "objection", "checkout", "upsell"],
    "E-11": ["automation", "workflow", "webhook", "api", "agent"],
    "E-12": ["analytics", "kpi", "experiment", "metrics", "optimization"],
    "E-13": ["memory", "context", "decision", "lesson", "provenance"],
}


def retrieve_for_engine(store: KnowledgeStore, engine_id: str, user_text: str,
                        project_context: Dict[str, Any] | None = None,
                        limit: int = 6) -> List[KnowledgeItem]:
    context = project_context or {}
    terms = list(ENGINE_TERMS.get(engine_id, []))
    text = f"{user_text} {context.get('goal', '')} {context.get('stage', '')} {context.get('audience', '')}"
    for token in text.lower().split():
        if len(token) >= 5:
            terms.append(token)
    # Small deterministic dedupe while preserving order
    seen = set()
    terms = [t for t in terms if not (t in seen or seen.add(t))]
    return store.search(terms, scope=context.get("scope", "global"), limit=limit)


def build_knowledge_pack(items: List[KnowledgeItem]) -> Dict[str, Any]:
    return {
        "knowledge_ids": [x.knowledge_id for x in items],
        "items": [x.to_dict() for x in items],
        "source_refs": sorted({ref for x in items for ref in x.source_refs}),
        "confidence": "high" if items and all(x.confidence == "high" for x in items) else "mixed",
    }
