from typing import Dict, Any, List
import re

TOPIC_TEMPLATES = {
    "Problem Education": [
        "3 mistakes founders make before validating a business idea",
        "Why founders rush to build before proving demand",
        "A simple way to spot validation risk before spending money",
        "The hidden cost of building before validating the problem",
    ],
    "Outcome Education": [
        "What a useful opportunity brief should help you decide",
        "A simpler path from business idea to validation",
        "Before vs after: making a business idea easier to validate",
        "What to prove first before building the product",
    ],
    "How-To / Workflow": [
        "A step-by-step workflow for validating a business idea",
        "A simple validation checklist for small-business founders",
        "How to turn market evidence into a validation test",
        "A beginner-friendly framework for testing demand",
    ],
    "Proof / Examples": [
        "Example: what a focused validation workflow looks like",
        "Breakdown of a practical market-validation use case",
        "What a useful validation deliverable should include",
        "Common objection: do I really need validation before building?",
    ],
    "Product / Offer": [
        "Who this validation service is for",
        "What the validation package helps you decide",
        "What is included in the first validation package",
        "Who should not buy a validation package yet",
    ],
}

def _clean_phrase(value: str, limit: int = 90) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    text = re.sub(r"^customers? (may |can |often )?", "", text, flags=re.I)
    text = re.sub(r"^small businesses? (may |can |often )?", "", text, flags=re.I)
    text = text.rstrip(". ")
    return text[:limit].rstrip() if text else "the target problem"

class TopicGenerator:
    def generate(self, pillars_pack: Dict[str, Any], problem: str = "", promise: str = "", audience: str = "", topics_per_pillar: int = 4) -> Dict[str, Any]:
        all_topics: List[Dict[str, Any]] = []
        for pillar in pillars_pack.get("pillars", []):
            for template in TOPIC_TEMPLATES.get(pillar["name"], [])[:topics_per_pillar]:
                all_topics.append({
                    "topic_id": f"T-{len(all_topics)+1:03d}",
                    "pillar_id": pillar["pillar_id"], "pillar": pillar["name"], "topic": template,
                    "problem_context": _clean_phrase(problem), "promise_context": _clean_phrase(promise),
                    "audience": _clean_phrase(audience),
                    "objective": "Teach one useful, actionable point and lead to the next practical step.",
                    "status": "IDEA",
                })
        return {"topic_count": len(all_topics), "topics": all_topics}
