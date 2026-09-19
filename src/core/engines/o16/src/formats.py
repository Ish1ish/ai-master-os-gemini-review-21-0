from typing import Dict, Any, List


class ContentFormatPlanner:
    def build(self, topics_pack: Dict[str, Any],
              platforms: List[str] | None = None) -> Dict[str, Any]:
        platforms = list(platforms or ["Instagram", "TikTok", "YouTube Shorts"])

        mapping = {
            "Problem Education": ["Short Video", "Carousel", "Text Post"],
            "Outcome Education": ["Short Video", "Carousel", "Case-style Post"],
            "How-To / Workflow": ["Tutorial Video", "Carousel", "Checklist Post"],
            "Proof / Examples": ["Demo Video", "Case Study", "Before/After"],
            "Product / Offer": ["Demo Video", "Offer Post", "FAQ Post"],
        }

        planned=[]
        for t in topics_pack.get("topics", []):
            formats = mapping.get(t["pillar"], ["Short Video"])
            planned.append({
                "topic_id":t["topic_id"],
                "recommended_formats":formats[:3],
                "platforms":platforms,
            })

        return {
            "format_plan":planned,
            "platforms":platforms,
        }
