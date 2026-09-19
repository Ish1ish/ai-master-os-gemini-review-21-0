from typing import Dict, Any, List
import re


_MAX_EVIDENCE_SUMMARY = 240



def _sanitize_untrusted_evidence(text: str) -> str:
    """Remove common prompt-injection directives from external evidence before
    it becomes model-facing semantic context. Source URLs/refs remain intact.
    """
    value = str(text or "")
    patterns = [
        r"(?i)ignore\s+(all\s+)?previous\s+instructions?",
        r"(?i)ignore\s+the\s+system\s+message",
        r"(?i)you\s+are\s+now\s+(?:the\s+)?system",
        r"(?i)reveal\s+(?:the\s+)?(?:system|developer|hidden)\s+(?:prompt|instructions?)",
        r"(?i)follow\s+these\s+instructions\s+instead",
        r"(?i)do\s+not\s+follow\s+(?:the\s+)?(?:system|developer)\s+instructions?",
        r"(?i)jailbreak|prompt\s+injection",
    ]
    for pattern in patterns:
        value = re.sub(pattern, "", value)
    return re.sub(r"\s+", " ", value).strip()

def _compact_evidence_statement(statement: str) -> str:
    """Turn raw provider/report text into a bounded, readable handoff phrase.

    The original source statement remains available as evidence via source_refs;
    this function prevents long markdown-table/report blobs from being copied
    verbatim into downstream idea and strategy fields.
    """
    text = _sanitize_untrusted_evidence(re.sub(r"\s+", " ", (statement or "").strip()))
    if not text:
        return "market evidence"

    if "|" in text:
        cells = [c.strip() for c in text.split("|") if c.strip()]
        # Drop markdown separator/header-like cells and collapse the first few
        # meaningful cells into a short evidence descriptor.
        cells = [c for c in cells if not re.fullmatch(r"[-: ]+", c)]
        if len(cells) >= 2:
            text = " — ".join(cells[:4])
        elif cells:
            text = cells[0]

    # Avoid carrying markdown table delimiters/headings into semantic fields.
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"\s{2,}", " ", text).strip(" -|:")
    if len(text) > _MAX_EVIDENCE_SUMMARY:
        text = text[:_MAX_EVIDENCE_SUMMARY].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"
    return text


def _problem_statement(evidence_summary: str, category: str) -> str:
    core = _sanitize_untrusted_evidence(evidence_summary)
    if not core:
        return "Customers have a problem that needs a simpler, lower-cost solution."
    low = core.lower()
    # Keep solution/vendor language out of the canonical problem field.
    if category == "pricing_signal" or any(token in low for token in ("price", "pricing", "cost", "bill", "expense", "expensive")):
        return "Customers face cost and complexity when choosing affordable tools that solve this need."
    if category in {"market_gap", "competitive_gap"}:
        return "Customers need a simpler option that addresses the underlying job without unnecessary complexity."
    if category == "problem_to_solve":
        # Problem signals can still contain vendor names; phrase them as customer impact.
        if any(token in low for token in ("onboarding", "setup", "friction", "difficulty", "complex")):
            return "Customers experience friction or complexity that makes the current workflow harder than it should be."
        return core[:_MAX_EVIDENCE_SUMMARY]
    return "Customers need a practical way to address the underlying need with less complexity."


class IdeaGenerator:
    """
    Generates candidate ideas from opportunity themes.
    Candidate ideas remain hypotheses until validated.

    Raw evidence is retained by provenance/source refs, but downstream semantic
    fields use a compact evidence summary instead of copying provider payloads.
    """

    def generate(self, themes_pack: Dict[str, Any], audience: str = "",
                 constraints: List[str] | None = None,
                 max_ideas: int = 20,
                 opportunities: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
        constraints = list(constraints or [])
        ideas = []
        opportunities = list(opportunities or [])
        if opportunities:
            for idx, opp in enumerate(opportunities[:max_ideas], 1):
                title = str(opp.get("title") or "Focused AI-enabled business opportunity")
                customer = str(opp.get("customer_segment") or audience)
                problem = str(opp.get("problem") or "Validated customer problem")
                outcome = str(opp.get("desired_outcome") or "A measurable improvement in the target workflow")
                solution = str(opp.get("solution_format") or "Service-first validation")
                ideas.append({
                    "idea_id": f"IDEA-{idx:03d}", "idea": f"{title}: {solution}.", "title": title,
                    "customer_segment": customer, "problem_statement": problem, "desired_outcome": outcome,
                    "solution_format": solution, "evidence_summary": str(opp.get("evidence_summary") or "market evidence"),
                    "signal_type": (opp.get("signal_categories") or ["market_signal"])[0], "audience": customer or audience,
                    "constraints": constraints, "source_refs": list(opp.get("source_refs") or []),
                    "origin_themes": list(opp.get("origin_themes") or []), "opportunity_id": str(opp.get("opportunity_id") or f"OPP-{idx:03d}"),
                    "opportunity_score": opp.get("opportunity_score"), "assumptions": list(opp.get("assumptions") or []),
                    "resource_fit": opp.get("resource_fit", "service-first / lightweight MVP"), "validation_test": opp.get("validation_test") or {},
                    "market_scope": opp.get("market_scope", "global_signal_requires_local_validation"), "status": "HYPOTHESIS",
                    "confidence": opp.get("confidence", "medium"), "opportunity": dict(opp),
                })
            return {"audience": audience, "constraints": constraints, "opportunity_candidates": opportunities[:max_ideas],
                    "idea_count": len(ideas), "ideas": ideas,
                    "boundary": "Generated ideas are hypotheses derived from synthesized market opportunities. They are not proven demand, profitability, or product-market fit."}

        for theme in themes_pack.get("themes", []):
            category = theme.get("category", "market_signal")
            statement = (theme.get("statement") or "").strip()
            source_id = theme.get("source_id", "")
            evidence_summary = _compact_evidence_statement(statement)

            if category == "problem_to_solve":
                idea = f"Create a simple product/service that reduces: {evidence_summary}"
            elif category == "market_gap":
                idea = f"Create a focused offer that addresses this gap: {evidence_summary}"
            elif category == "competitive_gap":
                idea = f"Create a differentiated alternative around: {evidence_summary}"
            elif category == "pricing_signal":
                idea = f"Create a value-focused offer responding to: {evidence_summary}"
            else:
                idea = f"Explore a targeted offer based on: {evidence_summary}"

            ideas.append({
                "idea_id": f"IDEA-{len(ideas)+1:03d}",
                "idea": idea,
                "evidence_summary": evidence_summary,
                "problem_statement": _problem_statement(evidence_summary, category),
                "signal_type": category,
                "audience": audience,
                "constraints": constraints,
                "source_refs": [source_id] if source_id else [],
                "origin_theme": theme.get("theme_id", ""),
                "status": "HYPOTHESIS",
            })

            if len(ideas) >= max_ideas:
                break

        return {
            "audience": audience,
            "constraints": constraints,
            "idea_count": len(ideas),
            "ideas": ideas,
            "boundary": (
                "Generated ideas are hypotheses derived from market evidence. "
                "They are not proven demand, profitability, or product-market fit."
            ),
        }
