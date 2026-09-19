from typing import Dict, Any, List


class ChannelPlanner:
    def build(self, audience: Dict[str, Any],
              objective: str = "validate acquisition") -> Dict[str, Any]:
        return {
            "objective": objective,
            "primary_channel_candidates": [
                {
                    "channel": "Organic Short-form Content",
                    "fit": "Useful when the offer can be demonstrated/educated through content.",
                    "test": "Consistent problem-first content with one CTA path.",
                },
                {
                    "channel": "Search / Intent",
                    "fit": "Useful when users actively search for the problem/solution.",
                    "test": "Test intent-aligned pages/content and measure qualified traffic.",
                },
                {
                    "channel": "Paid Acquisition",
                    "fit": "Useful after the offer and conversion path have enough evidence.",
                    "test": "Small-budget controlled creative/offer experiment.",
                },
            ],
            "channel_selection_rule": "Start with one primary channel whose audience fit and measurement are strongest; add channels only after evidence.",
        }
