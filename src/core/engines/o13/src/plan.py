def build_90_day_plan(strategy, idea, constraints=None):
    constraints=list(constraints or [])
    model=strategy.get("recommended_model",{})
    return {
        "phase_1_days_1_30":[
            "Validate the problem and target segment.",
            "Interview / collect customer evidence.",
            "Map current alternatives and objections.",
            "Build the smallest usable MVP/pilot.",
        ],
        "phase_2_days_31_60":[
            f"Run the first paid or high-intent validation using the {model.get('name','selected')} model.",
            "Measure conversion, activation, customer feedback, and basic economics.",
            "Refine the offer, onboarding, and positioning from evidence.",
        ],
        "phase_3_days_61_90":[
            "Double down on the strongest validated audience/message/channel.",
            "Document the repeatable delivery process.",
            "Add lightweight automation only where repetition is proven.",
            "Decide: scale, iterate, pivot, or stop.",
        ],
        "constraints":constraints,
        "success_gate":"Do not scale until demand + delivery feasibility + basic economics are supported by evidence.",
    }
