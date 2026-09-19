class ExpansionBuilder:
    def build(self, product_definition, offer):
        return {
            "expansion_paths": [
                {
                    "type": "Upsell",
                    "direction": "Add a higher-value layer only after core value is proven.",
                },
                {
                    "type": "Cross-sell",
                    "direction": "Offer adjacent products/services that solve a related validated problem.",
                },
                {
                    "type": "Retention",
                    "direction": "Improve onboarding, support, repeat use, and customer success before pushing expansion.",
                },
            ],
            "rule": "Expansion must follow demonstrated customer value, not be used to mask weak core conversion.",
        }
