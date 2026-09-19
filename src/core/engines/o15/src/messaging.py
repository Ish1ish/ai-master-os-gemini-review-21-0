class MessagingBuilder:
    def build(self, dna, positioning):
        return {
            "core_message": dna.get("brand_promise",""),
            "one_liner": positioning.get("positioning_statement",""),
            "message_pillars": [
                {
                    "pillar":"Problem",
                    "message":"We understand the specific friction the customer is trying to remove."
                },
                {
                    "pillar":"Outcome",
                    "message":"The brand focuses on a clear, useful customer outcome."
                },
                {
                    "pillar":"Simplicity",
                    "message":"The experience should feel easier and more practical than broad alternatives."
                },
                {
                    "pillar":"Proof",
                    "message":"Evidence, examples, and customer results matter more than hype."
                },
            ],
            "claim_rule": "Do not make performance, market, customer, or result claims without support.",
        }
