class BuyerQualifier:
    def build(self, product_definition, audience):
        return {
            "qualification_questions": [
                {
                    "question": "Does the buyer experience the target problem?",
                    "signal": "problem fit",
                },
                {
                    "question": "Is solving this problem a current priority?",
                    "signal": "urgency / priority",
                },
                {
                    "question": "Can the buyer access the required resources or budget?",
                    "signal": "resource fit",
                },
                {
                    "question": "Can the buyer realistically use the solution?",
                    "signal": "delivery fit",
                },
            ],
            "disqualifiers": [
                "No meaningful problem fit",
                "No current priority",
                "Requires unsupported outcomes",
            ],
        }
