class BrandDNABuilder:
    def build(self, product_definition, strategy, audience=""):
        positioning = strategy.get("recommendation_reason","")
        problem = product_definition.get("core_problem","")
        product_type = product_definition.get("product_type","")
        audience = audience or product_definition.get("target_audience","")

        return {
            "brand_purpose": "Make the defined customer outcome easier to understand, trust, and achieve.",
            "brand_mission": f"Help {audience or 'the target customer'} solve a focused problem through a clearer, simpler {product_type.lower()} experience.",
            "brand_promise": product_definition.get("core_promise",""),
            "audience": audience,
            "problem_space": problem,
            "strategic_anchor": positioning,
            "values": [
                "Clarity",
                "Practicality",
                "Customer progress",
                "Evidence over hype",
                "Simplicity"
            ],
            "personality": [
                "Clear",
                "Practical",
                "Confident",
                "Modern",
                "Helpful"
            ],
        }
