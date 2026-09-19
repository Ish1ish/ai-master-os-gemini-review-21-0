from typing import Dict, Any, List


class ContentPillarBuilder:
    def build(self, product_definition: Dict[str, Any],
              brand_dna: Dict[str, Any]) -> Dict[str, Any]:
        promise = product_definition.get("core_promise", "")
        problem = product_definition.get("core_problem", "")
        audience = brand_dna.get("audience", product_definition.get("target_audience", ""))

        return {
            "pillars": [
                {
                    "pillar_id": "P-01",
                    "name": "Problem Education",
                    "purpose": "Help the audience understand the problem, friction, and consequences.",
                    "audience": audience,
                    "anchor": problem,
                },
                {
                    "pillar_id": "P-02",
                    "name": "Outcome Education",
                    "purpose": "Show the desired result and what better looks like.",
                    "audience": audience,
                    "anchor": promise,
                },
                {
                    "pillar_id": "P-03",
                    "name": "How-To / Workflow",
                    "purpose": "Teach practical steps, systems, and implementation.",
                    "audience": audience,
                    "anchor": "Practical execution",
                },
                {
                    "pillar_id": "P-04",
                    "name": "Proof / Examples",
                    "purpose": "Use examples, demonstrations, and evidence to build trust.",
                    "audience": audience,
                    "anchor": "Evidence over hype",
                },
                {
                    "pillar_id": "P-05",
                    "name": "Product / Offer",
                    "purpose": "Connect the audience's problem and desired outcome to the product.",
                    "audience": audience,
                    "anchor": promise,
                },
            ],
            "pillar_rule": "Every content pillar should support awareness, trust, customer progress, or conversion.",
        }
