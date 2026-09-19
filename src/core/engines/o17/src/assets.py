from typing import Dict, Any, List


class AssetSpecBuilder:
    def build(self, brief: Dict[str, Any], layout: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "asset_type": "social content visual",
            "deliverables": [
                {
                    "type": "primary_visual",
                    "purpose": "Main content asset",
                    "required": True,
                },
                {
                    "type": "alternate_crop",
                    "purpose": "Platform adaptation",
                    "required": True,
                },
                {
                    "type": "text_overlay_version",
                    "purpose": "Readable hook/message version",
                    "required": True,
                },
            ],
            "requirements": [
                "Follow the brand visual direction.",
                "Keep the content idea immediately understandable.",
                "Protect safe areas.",
                "Keep text concise and readable.",
                "Do not add unsupported claims or fabricated proof.",
            ],
            "layout_reference": layout.get("composition", {}),
        }
