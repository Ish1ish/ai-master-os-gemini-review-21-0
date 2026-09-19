from typing import Any, Dict, List


VOLATILE_TERMS = {
    "today", "current", "latest", "now", "trend", "trending", "price",
    "pricing", "competitor", "platform", "policy", "2026", "recent"
}


def requires_live_research(user_text: str) -> bool:
    low = (user_text or "").lower()
    return any(term in low for term in VOLATILE_TERMS)


def check_knowledge_freshness(user_text: str, pack: Dict[str, Any]) -> Dict[str, Any]:
    live_required = requires_live_research(user_text)
    static_items = [
        item["knowledge_id"] for item in pack.get("items", [])
        if item.get("freshness") in {"static", "unknown"}
    ]
    return {
        "live_research_required": live_required,
        "static_items_used": static_items,
        "status": "REFRESH_REQUIRED" if live_required else "PASS",
        "message": (
            "Current/volatile claims require live research; static knowledge is retained only as framework/rules."
            if live_required else
            "Static knowledge is acceptable for framework/prompt logic in this run."
        ),
    }
