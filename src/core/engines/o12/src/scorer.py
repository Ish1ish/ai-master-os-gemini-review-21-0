from typing import Dict, Any, List


DEFAULT_WEIGHTS = {
    "evidence_fit": 0.30,
    "problem_strength": 0.20,
    "differentiation": 0.15,
    "feasibility": 0.15,
    "distribution": 0.10,
    "economics_hypothesis": 0.10,
}


def _score(text: str, keywords: list[str], base: float = 5.0) -> float:
    text = text.lower()
    hits = sum(1 for k in keywords if k in text)
    return min(10.0, base + hits * 1.2)


class IdeaScorer:
    """
    Scores ideas as decision aids, not as proof.
    """

    def score(self, ideas_pack: Dict[str, Any],
              market_context: Dict[str, Any] | None = None,
              weights: Dict[str, float] | None = None) -> Dict[str, Any]:
        weights = dict(DEFAULT_WEIGHTS)
        if weights:
            weights.update(weights)

        market_text = ""
        if market_context:
            market_text = " ".join(
                str(x.get("statement", ""))
                for x in market_context.get("findings", [])
            )

        scored = []
        for idea in ideas_pack.get("ideas", []):
            text = f"{idea.get('idea','')} {market_text}"

            evidence_fit = _score(
                text,
                ["evidence", "problem", "gap", "customer"],
                4.0,
            )
            problem_strength = _score(
                text,
                ["problem", "pain", "friction", "difficulty", "complex"],
                4.5,
            )
            differentiation = _score(
                text,
                ["differentiated", "focused", "alternative", "gap"],
                4.0,
            )
            feasibility = _score(
                text,
                ["simple", "focused", "small", "reduce"],
                4.5,
            )
            distribution = _score(
                text,
                ["customer", "audience", "market", "offer"],
                4.5,
            )
            economics = _score(
                text,
                ["value", "pricing", "cost"],
                4.0,
            )

            overall = (
                evidence_fit * weights["evidence_fit"] +
                problem_strength * weights["problem_strength"] +
                differentiation * weights["differentiation"] +
                feasibility * weights["feasibility"] +
                distribution * weights["distribution"] +
                economics * weights["economics_hypothesis"]
            )

            scored.append({
                **idea,
                "scores": {
                    "evidence_fit": round(evidence_fit, 2),
                    "problem_strength": round(problem_strength, 2),
                    "differentiation": round(differentiation, 2),
                    "feasibility": round(feasibility, 2),
                    "distribution": round(distribution, 2),
                    "economics_hypothesis": round(economics, 2),
                },
                "overall_score": round(overall, 2),
            })

        scored.sort(key=lambda x: (-x["overall_score"], x["idea_id"]))

        return {
            "weights": weights,
            "ranked_ideas": scored,
            "boundary": (
                "Idea scores are prioritization heuristics. They do not establish "
                "profitability, market size, demand certainty, or product-market fit."
            ),
        }
