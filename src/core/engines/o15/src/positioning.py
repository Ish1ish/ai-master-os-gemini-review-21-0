class BrandPositioningBuilder:
    def build(self, product_definition, strategy, dna):
        audience = dna.get("audience","the target customer")
        problem = dna.get("problem_space","the target problem")
        product_type = product_definition.get("product_type","solution")

        return {
            "positioning_statement": (
                f"For {audience}, this {product_type.lower()} is a focused solution for {problem}, "
                "designed around a simpler path to the desired outcome."
            ),
            "category_direction": "Focused, outcome-oriented solution",
            "differentiation_axes": [
                "Sharper audience/problem focus",
                "Simpler onboarding",
                "Outcome clarity",
                "Practical proof and examples",
            ],
            "competitive_posture": "Focused challenger rather than broad generalist",
            "positioning_boundary": (
                "Positioning is a strategic hypothesis until validated against current competitors "
                "and customer response."
            ),
        }
