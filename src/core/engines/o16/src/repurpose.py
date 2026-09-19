from typing import Dict, Any


class Repurposer:
    def build(self, content_item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "source_topic_id": content_item.get("topic_id"),
            "repurposed_versions": [
                {"format":"Short Video","purpose":"Hook + one key insight + CTA"},
                {"format":"Carousel","purpose":"Step-by-step visual breakdown"},
                {"format":"Text Post","purpose":"Concise takeaway + question"},
                {"format":"Story / Short Update","purpose":"One insight + interactive prompt"},
            ],
            "repurpose_rule": "Preserve the core message while adapting structure to the format.",
        }
