class FollowUpBuilder:
    def build(self, offer, audience):
        return {
            "sequence": [
                {
                    "step": 1,
                    "timing": "Initial follow-up",
                    "goal": "Clarify the problem and next step.",
                    "rule": "Relevant and concise; no pressure tactics.",
                },
                {
                    "step": 2,
                    "timing": "Value follow-up",
                    "goal": "Share useful context, proof, or demonstration.",
                    "rule": "Add value instead of repeating the pitch.",
                },
                {
                    "step": 3,
                    "timing": "Decision follow-up",
                    "goal": "Resolve remaining questions or objections.",
                    "rule": "Make the next action explicit.",
                },
                {
                    "step": 4,
                    "timing": "Close-the-loop",
                    "goal": "Respectfully close or recycle the conversation.",
                    "rule": "No fake scarcity or manipulation.",
                },
            ]
        }
