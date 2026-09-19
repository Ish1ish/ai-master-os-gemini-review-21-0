from typing import Dict, Any, List


class CampaignBuilder:
    def build(self, offer: Dict[str, Any],
              funnel: Dict[str, Any],
              channels: Dict[str, Any],
              content: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return {
            "campaign_objective": "Generate qualified demand and learn which message/creative/offer combination converts.",
            "campaign_structure": [
                {
                    "phase": "Problem",
                    "message": "Make the customer problem visible and relevant.",
                    "cta": "Learn / Diagnose",
                },
                {
                    "phase": "Solution",
                    "message": "Show the simpler path and why this approach is useful.",
                    "cta": "See How / Explore",
                },
                {
                    "phase": "Proof",
                    "message": "Use evidence, examples, demonstrations, and objections.",
                    "cta": "Evaluate",
                },
                {
                    "phase": "Offer",
                    "message": "Present the offer, scope, fit, and next step clearly.",
                    "cta": "Take the Next Step",
                },
            ],
            "primary_experiment_axes": [
                "Message / angle",
                "Creative / hook",
                "Offer framing",
                "CTA",
                "Landing/conversion flow",
            ],
        }
