from datetime import datetime, timezone
from typing import Dict, Any, List
from urllib.parse import urlparse
import re
from .models import SourceRecord, EvidenceItem

_LOCAL_STRONG = (
    "egypt", "egyptian", "cairo", "giza", "alexandria", "mansoura", "tanta",
    "ismailia", "portsaid", "suez", "aswan", "luxor", "new cairo", "10th of ramadan",
    "el shorouk", "nasr city", "smouha", "heliopolis", "dokki", "maadi"
)
_LOCAL_TRANSACTION = ("egp", "جنيه", "ج.م", "المصري", "مصر", "مصري")
_GENERIC_IDEA = (
    "business idea generator", "startup ideas", "idea generator", "money-making website",
    "ai business ideas", "validated startup opportunities", "business validation platform"
)
_REGIONAL = ("mena", "middle east", "gcc", "uae", "saudi", "jordan", "lebanon", "morocco")


def _domain(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower().removeprefix("www.")
    except Exception:
        return ""


def _geo_profile(title: str, url: str, snippet: str) -> Dict[str, Any]:
    title_text = str(title or "").lower()
    url_text = str(url or "").lower()
    snippet_text = str(snippet or "").lower()
    text = f"{title_text} {url_text} {snippet_text}"
    domain = _domain(url)

    generic_idea = any(x in text for x in _GENERIC_IDEA)
    strong_hits = sum(1 for x in _LOCAL_STRONG if x in text)
    transaction_hits = sum(1 for x in _LOCAL_TRANSACTION if x in text)
    eg_domain = domain.endswith(".eg") or ".com.eg" in domain or ".org.eg" in domain

    # A generic global idea article mentioning Egypt once is not local evidence.
    if generic_idea and not eg_domain and strong_hits == 0 and transaction_hits == 0:
        return {"score": 0.15, "role": "global_context", "reason": "generic_global_idea_source"}

    if eg_domain or (strong_hits >= 2) or (strong_hits >= 1 and transaction_hits >= 1):
        reasons = []
        if eg_domain:
            reasons.append(".eg_domain")
        if strong_hits:
            reasons.append(f"egypt_locality_hits:{strong_hits}")
        if transaction_hits:
            reasons.append(f"local_transaction_hits:{transaction_hits}")
        return {"score": 1.0, "role": "local", "reason": ",".join(reasons)}

    if any(x in text for x in _REGIONAL):
        return {"score": 0.6, "role": "regional", "reason": "regional_signal"}

    return {"score": 0.3, "role": "global_context", "reason": "global_or_unspecified"}


def _geo_relevance(title: str, url: str, snippet: str) -> float:
    return float(_geo_profile(title, url, snippet)["score"])


def build_evidence_pack(search_payloads: List[Dict[str, Any]],
                        max_results_per_query: int = 5) -> Dict[str, Any]:
    sources = []
    evidence = []
    source_by_url: Dict[str, Dict[str, Any]] = {}
    source_ids: Dict[str, str] = {}

    for payload in search_payloads:
        for item in payload.get("results", [])[:max_results_per_query]:
            url = str(item.get("url") or "").strip()
            if not url:
                continue
            if url not in source_by_url:
                sid = f"SRC-{len(source_by_url)+1:03d}"
                source_ids[url] = sid
                src = SourceRecord(
                    source_id=sid,
                    title=item.get("title", ""),
                    url=url,
                    source_type=item.get("source_type", "web"),
                    published_at=item.get("published_at", ""),
                    accessed_at=datetime.now(timezone.utc).isoformat(),
                    authority=item.get("authority", ""),
                    notes="Collected by O11 research provider.",
                )
                source_by_url[url] = src.to_dict()
                sources.append(source_by_url[url])

            source_id = source_ids[url]
            excerpt = str(item.get("snippet", "") or "")
            claim = re.sub(r"\s+", " ", excerpt.strip())[:280]
            geo = _geo_profile(item.get("title", ""), url, excerpt)
            item_dict = EvidenceItem(
                evidence_id=f"EVD-{len(evidence)+1:04d}",
                claim=claim,
                source_id=source_id,
                excerpt=excerpt,
                confidence="medium",
                freshness="current",
            ).to_dict()
            item_dict.update({
                "geographic_relevance": geo["score"],
                "source_role": geo["role"],
                "geographic_reason": geo["reason"],
            })
            evidence.append(item_dict)

    return {
        "source_count": len(sources),
        "evidence_count": len(evidence),
        "sources": sources,
        "evidence": evidence,
    }
