from typing import Dict, Any


class VisualBriefBuilder:
    def build(self, content_item: Dict[str, Any], brand_output: Dict[str, Any],
              platform: str = "Instagram") -> Dict[str, Any]:
        brand_dna = brand_output.get("brand_dna", {})
        positioning = brand_output.get("positioning", {})
        visual = brand_output.get("visual_direction", {})
        voice = brand_output.get("voice", {})

        return {
            "asset_id": f"VIS-{content_item.get('topic_id', 'UNKNOWN')}",
            "platform": platform,
            "content_topic": content_item.get("topic", ""),
            "content_pillar": content_item.get("pillar", ""),
            "objective": "Make the content idea immediately understandable and visually memorable.",
            "audience": brand_dna.get("audience", ""),
            "brand_personality": brand_dna.get("personality", []),
            "positioning_anchor": positioning.get("positioning_statement", ""),
            "visual_principles": visual.get("visual_principles", []),
            "voice_anchor": voice.get("voice", {}).get("primary", "Clear"),
            "creative_direction": "Use a clear visual hierarchy, one dominant message, and a strong focal point.",
        }
