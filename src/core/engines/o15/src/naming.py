from typing import List, Dict


class NamingDirectionBuilder:
    def build(self, dna, strategy, candidates: List[str] | None = None) -> Dict:
        candidates = list(candidates or [])
        return {
            "naming_principles": [
                "Easy to pronounce",
                "Easy to remember",
                "Relevant to the brand promise without being overly literal",
                "Flexible enough for future product expansion",
                "Avoid confusing similarity to known competitors",
            ],
            "style_directions": [
                "Short and modern",
                "Outcome-oriented",
                "Distinctive but simple",
                "Professional with a contemporary feel",
            ],
            "candidate_names": candidates,
            "availability_check_required": True,
            "availability_boundary": (
                "Trademark, domain, handle, and business-name availability must be checked "
                "against current sources before adoption."
            ),
        }
