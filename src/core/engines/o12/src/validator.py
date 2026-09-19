from typing import Dict, Any, List


class IdeaValidator:
    """
    Produces a validation backlog for each candidate.
    """

    def build_validation_plan(self, ranked_pack: Dict[str, Any]) -> Dict[str, Any]:
        plans = []

        for idea in ranked_pack.get("ranked_ideas", []):
            checks = [
                {
                    "test": "Customer Need",
                    "question": "Do target customers actually experience the stated problem?",
                    "evidence": "Interviews, reviews, support/customer language, search behavior",
                },
                {
                    "test": "Willingness to Pay",
                    "question": "Would the target buyer pay for this outcome?",
                    "evidence": "Offer tests, preorders, paid pilots, pricing interviews",
                },
                {
                    "test": "Competition",
                    "question": "What alternatives already solve this and where is the gap?",
                    "evidence": "Current competitor research",
                },
                {
                    "test": "Distribution",
                    "question": "Can the audience be reached economically?",
                    "evidence": "Channels, communities, partnerships, ad/content tests",
                },
                {
                    "test": "Feasibility",
                    "question": "Can a useful MVP be built within constraints?",
                    "evidence": "Resource/time/tool assessment",
                },
            ]
            experiment = {
                "experiment_id": f"VAL-{idea.get('idea_id','IDEA')}",
                "hypothesis": "The target customer experiences the stated problem often enough to justify a focused solution.",
                "who": idea.get("customer_segment") or "target customers",
                "sample_size": 10,
                "method": "Interview or observe 10 target customers and document one real recurring workflow.",
                "measure": [
                    "problem_frequency",
                    "time_or_effort_cost",
                    "current_workaround",
                    "willingness_to_test_or_pay",
                ],
                "success_threshold": {
                    "problem_confirmation": "At least 6/10 report the problem as recurring and material.",
                    "high_intent": "At least 3/10 agree to a pilot, test, or concrete next step.",
                },
                "thresholds_machine": {
                    "problem_confirmation": {"operator": ">=", "value": 6, "description": "At least 6/10 report the problem as recurring and material."},
                    "high_intent": {"operator": ">=", "value": 3, "description": "At least 3/10 agree to a pilot, test, or concrete next step."},
                },
                "decision_rule": "GO when both thresholds are met; otherwise refine the problem/segment and re-test.",
                "timebox_days": 7,
                "external_action_required": False,
            }
            plans.append({
                "idea_id": idea.get("idea_id"),
                "validation_priority": (
                    "HIGH" if idea.get("overall_score", 0) >= 7.0 else
                    "MEDIUM" if idea.get("overall_score", 0) >= 5.0 else
                    "LOW"
                ),
                "checks": checks,
                "validation_experiment": experiment,
            })

        return {
            "idea_validation_plans": plans,
            "status": "READY_FOR_VALIDATION",
        }
