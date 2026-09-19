class ConversionCopyBuilder:
    def build(self, product_definition, brand_output, offer, audience):
        segment = audience.get("primary_segment", "")
        promise = offer.get("core_promise", "")
        offer_name = offer.get("offer_name") or product_definition.get("product_type") or "Focused Offer"
        return {
            "landing_page": {
                "hero": {
                    "headline": f"{offer_name}: {promise}",
                    "subheadline": f"Built for {segment}.",
                    "cta": "Take the next step",
                },
                "sections": [
                    "Problem / pain",
                    "Desired outcome",
                    "How it works",
                    "What is included",
                    "Proof / examples",
                    "FAQ / objections",
                    "Offer + next step",
                ],
            },
            "listing": {
                "title_direction": offer_name,
                "benefit_bullets": [
                    "Clear customer outcome",
                    "Focused scope",
                    "Practical onboarding",
                    "Examples / guidance",
                ],
                "cta": "Get started",
            },
            "copy_rules": [
                "Lead with customer outcome.",
                "Make scope and fit explicit.",
                "Use proof only when available.",
                "Avoid fake urgency, scarcity, guarantees, and unsupported statistics.",
            ],
        }
