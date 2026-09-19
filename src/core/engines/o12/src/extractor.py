from typing import Dict, Any, List
from collections import Counter
import re


class OpportunityExtractor:
    """
    Converts market findings into opportunity themes.
    Conservative by design: themes are hypotheses derived from evidence,
    not claims that an opportunity is proven.
    """

    def extract_themes(self, market_report: Dict[str, Any]) -> Dict[str, Any]:
        findings = market_report.get("findings", [])
        themes = []

        for i, finding in enumerate(findings, 1):
            statement = (finding.get("statement") or "").strip()
            if not statement:
                continue

            text = statement.lower()

            # Lightweight deterministic theme extraction.
            if any(k in text for k in ["problem", "friction", "pain", "difficulty", "complex"]):
                category = "problem_to_solve"
            elif any(k in text for k in ["gap", "unmet", "missing", "lack"]):
                category = "market_gap"
            elif any(k in text for k in ["competitor", "alternative", "existing"]):
                category = "competitive_gap"
            elif any(k in text for k in ["price", "pricing", "cost", "expensive"]):
                category = "pricing_signal"
            else:
                category = "market_signal"

            themes.append({
                "theme_id": f"THEME-{i:03d}",
                "category": category,
                "statement": statement,
                "source_id": finding.get("source_id", ""),
                "confidence": finding.get("confidence", "medium"),
            })

        return {
            "source_count": market_report.get("source_count", 0),
            "evidence_count": market_report.get("evidence_count", 0),
            "themes": themes,
        }
