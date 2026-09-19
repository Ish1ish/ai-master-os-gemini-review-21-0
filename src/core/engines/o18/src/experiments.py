from typing import Dict, Any, List


class MarketingExperimentPlanner:
    def build(self, campaign: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "experiments": [
                {
                    "experiment_id": "MKT-EXP-01",
                    "hypothesis": "A problem-first message produces more qualified attention than a feature-first message.",
                    "control": "Feature-first message",
                    "variant": "Problem-first message",
                    "primary_metric": "Qualified conversion rate",
                },
                {
                    "experiment_id": "MKT-EXP-02",
                    "hypothesis": "A demonstration-oriented creative increases qualified intent.",
                    "control": "Static explanatory creative",
                    "variant": "Demonstration creative",
                    "primary_metric": "Qualified click / lead rate",
                },
                {
                    "experiment_id": "MKT-EXP-03",
                    "hypothesis": "A clearer low-friction CTA improves conversion.",
                    "control": "Generic CTA",
                    "variant": "Specific next-step CTA",
                    "primary_metric": "Conversion rate",
                },
            ],
            "decision_rule": "Change one major variable at a time where practical and use the primary business metric rather than vanity metrics alone.",
        }
