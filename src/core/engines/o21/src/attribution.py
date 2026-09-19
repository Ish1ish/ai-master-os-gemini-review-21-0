from typing import Dict, Any, List

class AttributionEngine:
    def summarize(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        by_channel: Dict[str, Dict[str, int]] = {}
        for e in events:
            channel = e.get("properties", {}).get("channel", "unknown")
            by_channel.setdefault(channel, {"touches": 0, "conversions": 0})
            by_channel[channel]["touches"] += 1
            if e["event_type"] in {"purchase", "signup", "qualified_lead"}:
                by_channel[channel]["conversions"] += 1
        for d in by_channel.values():
            d["observed_conversion_rate"] = d["conversions"] / d["touches"] if d["touches"] else 0.0
        return {
            "model":"descriptive_observed_rate",
            "channels":by_channel,
            "causal_attribution_claim_allowed":False,
        }
