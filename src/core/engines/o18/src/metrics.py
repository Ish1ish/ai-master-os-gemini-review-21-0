from typing import Dict, Any


class MarketingMetrics:
    def build(self, funnel: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "core_kpis": [
                {
                    "kpi": "Qualified Attention",
                    "stage": "Awareness",
                    "why": "Measures whether the right people notice and engage with the message.",
                },
                {
                    "kpi": "Qualified Lead / Intent Rate",
                    "stage": "Consideration",
                    "why": "Measures movement from attention to meaningful intent.",
                },
                {
                    "kpi": "Conversion Rate",
                    "stage": "Conversion",
                    "why": "Measures the offer and conversion path.",
                },
                {
                    "kpi": "Cost per Acquisition",
                    "stage": "Conversion",
                    "why": "Measures acquisition efficiency.",
                },
                {
                    "kpi": "Contribution / Margin",
                    "stage": "Economics",
                    "why": "Prevents scaling unprofitable acquisition.",
                },
                {
                    "kpi": "Activation / Retention",
                    "stage": "Retention",
                    "why": "Checks whether customers successfully use and continue with the solution.",
                },
            ],
            "north_star_rule": "Choose the KPI closest to the business outcome being optimized; never optimize a vanity metric in isolation.",
        }
