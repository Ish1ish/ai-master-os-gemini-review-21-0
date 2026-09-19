class ObjectionHandler:
    OBJECTIONS = [
        ("Price", "Explain scope, value, alternatives, and expected customer effort without claiming guaranteed ROI."),
        ("Trust", "Use proof, examples, process transparency, and clear limitations."),
        ("Timing", "Clarify the cost of waiting and the smallest useful first step without creating fake urgency."),
        ("Fit", "State who the offer is for and who should not buy yet."),
        ("Complexity", "Show the onboarding path and reduce the first-step friction."),
    ]

    def build(self):
        return {
            "objections": [
                {
                    "objection": name,
                    "response_direction": direction,
                }
                for name, direction in self.OBJECTIONS
            ]
        }
