from typing import Dict, Any, List


class AudiencePlanner:
    def build(self, product_definition: Dict[str, Any],
              market_report: Dict[str, Any] | None = None) -> Dict[str, Any]:
        market_report = market_report or {}
        audience = product_definition.get("target_audience", "")
        problem = product_definition.get("core_problem", "")
        promise = product_definition.get("core_promise", "")

        return {
            "primary_segment": audience,
            "problem": problem,
            "desired_outcome": promise,
            "segment_priority_rule": "Prioritize the segment with the strongest evidence of pain, fit, reachability, and willingness to act.",
            "channel_inputs": [
                "Where the audience already pays attention",
                "Where intent is visible",
                "Where the offer can be demonstrated clearly",
            ],
            "evidence_refs": [
                f.get("source_id")
                for f in market_report.get("findings", [])
                if f.get("source_id")
            ][:10],
        }
