from typing import Dict, Any


class CaptionBuilder:
    def build(self, topic: Dict[str, Any], hook: str,
              voice: Dict[str, Any], cta: str) -> Dict[str, Any]:
        return {
            "topic_id": topic.get("topic_id"),
            "hook": hook,
            "caption": (
                f"{hook}\n\n"
                "Give the audience one clear insight, one practical action, "
                "and one reason the next step matters.\n\n"
                f"CTA: {cta}"
            ),
            "cta": cta,
            "claim_rule": "Do not add unsupported statistics, testimonials, or guarantees.",
        }
