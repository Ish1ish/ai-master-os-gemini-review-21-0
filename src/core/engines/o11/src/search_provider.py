from typing import Callable, Dict, Any, List, Optional
import re


def _sanitize_untrusted_text(text: Any) -> str:
    value = str(text or "")
    patterns = [
        r"(?i)ignore\s+(?:all\s+)?previous\s+instructions?",
        r"(?i)ignore\s+the\s+system\s+message",
        r"(?i)reveal\s+(?:the\s+)?(?:system|developer|hidden)\s+(?:prompt|instructions?)",
        r"(?i)follow\s+these\s+instructions\s+instead",
        r"(?i)do\s+not\s+follow\s+(?:the\s+)?(?:system|developer)\s+instructions?",
        r"(?i)jailbreak|prompt\s+injection",
    ]
    for pattern in patterns:
        value = re.sub(pattern, "", value)
    return re.sub(r"\s+", " ", value).strip()


class SearchProvider:
    """Host-injected current-research provider with fail-closed shape checks."""

    def __init__(self, provider: Optional[Callable[[str], Dict[str, Any]]] = None):
        self.provider = provider

    def search(self, query: str) -> Dict[str, Any]:
        if self.provider is None:
            return {
                "status": "UNAVAILABLE",
                "reason": "search_provider_not_configured",
                "query": query,
            }
        try:
            result = self.provider(query)
        except Exception as exc:
            return {
                "status": "UNAVAILABLE",
                "reason": f"search_provider_exception:{type(exc).__name__}",
                "query": query,
            }
        if not isinstance(result, dict):
            return {"status": "INVALID_RESPONSE", "reason": "provider_result_not_object", "query": query}
        raw_results = result.get("results")
        if not isinstance(raw_results, list):
            return {"status": "INVALID_RESPONSE", "reason": "provider_results_not_list", "query": query}
        normalized: List[Dict[str, Any]] = []
        for idx, item in enumerate(raw_results[:20]):
            if not isinstance(item, dict):
                return {"status": "INVALID_RESPONSE", "reason": "provider_result_item_not_object", "query": query, "index": idx}
            url = str(item.get("url") or "").strip()
            snippet = item.get("snippet") or item.get("content") or ""
            if not url or not str(snippet).strip():
                continue
            normalized.append({
                "title": _sanitize_untrusted_text(item.get("title")),
                "url": url,
                "snippet": _sanitize_untrusted_text(snippet),
                "published_at": str(item.get("published_at") or ""),
                "source_type": str(item.get("source_type") or "web"),
                "authority": _sanitize_untrusted_text(item.get("authority")),
            })
        if not normalized:
            return {"status": "INVALID_RESPONSE", "reason": "provider_no_usable_results", "query": query}
        return {"status": "SUCCESS", "query": query, "results": normalized}
