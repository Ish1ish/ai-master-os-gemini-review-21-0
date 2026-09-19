from typing import Dict, Any, List
from .extractor import OpportunityExtractor
from .opportunity import synthesize_opportunities
from .generator import IdeaGenerator
from .scorer import IdeaScorer
from .validator import IdeaValidator
from .qa import validate_idea_output
from src.handoff_contracts import build_idea_to_strategy_handoff, validate_semantic_handoff


class RealIdeaEngine:
    def __init__(self):
        self.extractor = OpportunityExtractor()
        self.generator = IdeaGenerator()
        self.scorer = IdeaScorer()
        self.validator = IdeaValidator()

    def build(self, market_report: Dict[str, Any],
              audience: str = "",
              constraints: List[str] | None = None,
              max_ideas: int = 20) -> Dict[str, Any]:

        themes = self.extractor.extract_themes(market_report)
        opportunities = synthesize_opportunities(market_report, audience=audience, constraints=constraints, max_candidates=min(5, max_ideas))
        ideas = self.generator.generate(themes, audience=audience, constraints=constraints, max_ideas=max_ideas, opportunities=opportunities)
        scores = self.scorer.score(ideas, market_context=market_report)
        validation = self.validator.build_validation_plan(scores)
        qa = validate_idea_output(themes, ideas, scores, validation)
        strategy_handoff = {}
        handoff_qa = {"status": "FAIL", "contract": "idea_to_strategy_v1", "issues": [{"type": "no_ranked_idea"}]}
        if scores.get("ranked_ideas"):
            strategy_handoff = build_idea_to_strategy_handoff(scores["ranked_ideas"][0])
            handoff_qa = validate_semantic_handoff(strategy_handoff, contract="idea_to_strategy_v1")
            if handoff_qa["status"] != "PASS":
                qa = dict(qa)
                qa["status"] = "FAIL"
                qa["issues"] = list(qa.get("issues") or []) + [{"type": "invalid_idea_to_strategy_handoff", "details": handoff_qa["issues"]}]

        return {
            "status": "COMPLETE" if qa["status"] == "PASS" and handoff_qa["status"] == "PASS" else "FAILED",
            "engine_id": "E-03",
            "engine_version": "O12-v1.1-O41",
            "themes": themes,
            "opportunity_candidates": opportunities,
            "ideas": ideas,
            "scores": scores,
            "validation": validation,
            "strategy_handoff": strategy_handoff,
            "handoff_qa": handoff_qa,
            "qa": qa,
        }
