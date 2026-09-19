from typing import Dict, Any


PLATFORM_SPECS = {
    "Instagram": {
        "feed": "4:5 preferred for vertical feed creative",
        "story_reel": "9:16",
        "safe_area": "Keep key text and faces away from edges/UI overlays.",
    },
    "TikTok": {
        "vertical_video": "9:16",
        "safe_area": "Keep key text away from top/bottom interface zones.",
    },
    "YouTube Shorts": {
        "vertical_video": "9:16",
        "safe_area": "Keep primary subject/text inside the central readable area.",
    },
    "YouTube": {
        "thumbnail": "16:9",
        "safe_area": "Keep title/face focal points readable at small sizes.",
    },
}


class LayoutPlanner:
    def build(self, brief: Dict[str, Any]) -> Dict[str, Any]:
        platform = brief.get("platform", "Instagram")
        spec = PLATFORM_SPECS.get(platform, {
            "default": "Adapt to current platform specifications.",
            "safe_area": "Keep critical content away from interface overlays.",
        })

        return {
            "canvas": spec,
            "composition": {
                "hierarchy": [
                    "Primary visual focal point",
                    "Headline / hook",
                    "Supporting context",
                    "CTA or next step",
                ],
                "alignment": "Use a consistent grid and clear spacing.",
                "contrast": "Ensure text remains readable against the background.",
                "focal_point": "One dominant subject or visual idea.",
            },
            "layout_rule": "Do not overcrowd the frame; one visual idea per asset.",
        }
