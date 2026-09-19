from typing import Dict, Any, List


class FunnelBuilder:
    def build(self, audience: Dict[str, Any],
              offer: Dict[str, Any],
              content: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return {
            "stages": [
                {
                    "stage": "Awareness",
                    "goal": "Reach the right audience with a relevant problem/insight.",
                    "primary_assets": ["Educational content", "Short video", "Carousel"],
                    "metric_candidates": ["Reach", "Engagement", "Qualified attention"],
                },
                {
                    "stage": "Consideration",
                    "goal": "Build trust and explain the solution.",
                    "primary_assets": ["How-to", "Demo", "Proof", "FAQ"],
                    "metric_candidates": ["Profile/landing visits", "Lead rate", "Qualified interest"],
                },
                {
                    "stage": "Conversion",
                    "goal": "Turn intent into a purchase, booking, signup, or paid pilot.",
                    "primary_assets": ["Offer page", "Sales copy", "CTA", "Checkout"],
                    "metric_candidates": ["Conversion rate", "Cost per acquisition", "Revenue"],
                },
                {
                    "stage": "Retention / Expansion",
                    "goal": "Create repeat use, referrals, or expansion.",
                    "primary_assets": ["Onboarding", "Support", "Follow-up", "Upsell/cross-sell"],
                    "metric_candidates": ["Activation", "Repeat purchase", "Retention", "Referral"],
                },
            ],
            "funnel_rule": "Instrument each stage and diagnose the first meaningful bottleneck before adding complexity.",
        }
