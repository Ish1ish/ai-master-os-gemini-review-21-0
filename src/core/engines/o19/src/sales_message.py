class SalesMessageBuilder:
    def build(self, product_definition, brand_output, offer, audience):
        promise = offer.get("core_promise") or product_definition.get("core_promise", "")
        segment = audience.get("primary_segment", "") or product_definition.get("target_audience", "")
        positioning = brand_output.get("positioning", {}).get("positioning_statement", "")
        offer_name = offer.get("offer_name") or product_definition.get("product_type") or "Focused Offer"

        return {
            "headline_direction": f"{offer_name}: {promise}",
            "value_proposition": f"For {segment}, deliver {promise} through {offer_name.lower()} and a focused, practical validation path.",
            "problem_to_outcome_bridge": "Start with the customer's problem, explain the outcome, then show the mechanism.",
            "positioning_support": positioning,
            "proof_rule": "Use only verified evidence, demonstrations, examples, or real customer proof.",
            "claim_boundary": "Do not promise guaranteed outcomes or fabricate proof."
        }
