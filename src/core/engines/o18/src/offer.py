from typing import Dict, Any


class OfferBuilder:
    def build(self, product_definition: Dict[str, Any],
              strategy: Dict[str, Any]) -> Dict[str, Any]:
        product_name = str(product_definition.get("product_name_placeholder") or "").strip()
        product_type = str(product_definition.get("product_type") or "").strip()
        offer_name = product_name or (f"{product_type} Offer" if product_type else "Focused Validation Offer")
        return {
            "offer_name": offer_name,
            "core_promise": product_definition.get("core_promise", ""),
            "mechanism": product_definition.get("primary_use_case") or "A focused solution designed around one primary customer outcome.",
            "included": [
                "Core product/service outcome", "Onboarding / setup", "Guidance / examples", "Support or next-step path",
            ],
            "risk_reversal_direction": "Reduce uncertainty with clear scope, proof, examples, or a low-friction first step.",
            "offer_boundary": "Do not promise outcomes that are not supported by evidence.",
        }
