from typing import Dict, Any
from collections import Counter


class MarketAnalyzer:
    def analyze(self, request: str, plan: Dict[str, Any], evidence_pack: Dict[str, Any]) -> Dict[str, Any]:
        evidence = evidence_pack.get("evidence", [])
        sources = evidence_pack.get("sources", [])
        keyword_counter = Counter()
        for e in evidence:
            for token in e.get("claim", "").lower().split():
                if len(token) >= 6 and token.isalpha():
                    keyword_counter[token] += 1
        top_terms = [k for k, _ in keyword_counter.most_common(12)]

        local_evidence = [e for e in evidence if e.get("source_role") == "local"]
        regional_evidence = [e for e in evidence if e.get("source_role") == "regional"]
        local_sources = {e.get("source_id") for e in local_evidence if e.get("source_id")}

        # "Supported" requires more than one local signal; a single local page is not enough
        # to establish an Egypt-wide decision boundary.
        evidence_boundary = (
            "local_evidence_supported"
            if len(local_sources) >= 2 and len(local_evidence) >= 3
            else "global_signal_requires_local_validation"
        )
        warnings = []
        if not local_evidence:
            warnings.append("No sufficiently local evidence was found in the current research pack.")
        elif evidence_boundary != "local_evidence_supported":
            warnings.append("Local evidence exists but is below the minimum support threshold; treat the result as a hypothesis.")

        return {
            "request": request,
            "research_dimensions": plan.get("dimensions", []),
            "source_count": len(sources),
            "evidence_count": len(evidence),
            "local_source_count": len(local_sources),
            "local_evidence_count": len(local_evidence),
            "regional_evidence_count": len(regional_evidence),
            "evidence_boundary": evidence_boundary,
            "top_terms": top_terms,
            "warnings": warnings,
            "findings": [
                {
                    "finding_id": f"F-{i+1:03d}",
                    "statement": e.get("claim", ""),
                    "source_id": e.get("source_id", ""),
                    "confidence": e.get("confidence", "medium"),
                    "source_role": e.get("source_role", "global_context"),
                    "geographic_reason": e.get("geographic_reason", ""),
                }
                for i, e in enumerate(evidence[:12]) if e.get("claim")
            ],
            "boundary": (
                "This report organizes collected evidence. It does not by itself prove "
                "profitability, market size, demand, or causality unless supported by "
                "appropriate evidence."
            ),
        }
