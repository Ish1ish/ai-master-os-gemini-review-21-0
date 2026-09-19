from typing import Dict, Any


class VisualPromptBuilder:
    def image_prompt(self, brief: Dict[str, Any], layout: Dict[str, Any]) -> str:
        personality = ", ".join(brief.get("brand_personality", []))
        principles = ", ".join(brief.get("visual_principles", []))

        return (
            f"Create a branded visual for {brief.get('platform','the target platform')}. "
            f"Topic: {brief.get('content_topic','')}. "
            f"Audience: {brief.get('audience','')}. "
            f"Brand personality: {personality}. "
            f"Visual principles: {principles}. "
            f"Direction: {brief.get('creative_direction','')}. "
            f"Composition: one dominant focal point, clear hierarchy, readable headline, "
            f"supporting context, and a clear CTA/next step. "
            f"Platform guidance: {layout.get('canvas',{})}. "
            f"Do not fabricate statistics, testimonials, logos, or proof."
        )

    def video_prompt(self, brief: Dict[str, Any], layout: Dict[str, Any]) -> str:
        return (
            f"Create a short-form vertical video concept for {brief.get('platform','the target platform')}. "
            f"Topic: {brief.get('content_topic','')}. "
            f"Open with a clear focal visual and readable hook. "
            f"Maintain strong visual hierarchy, simple scene changes, brand-consistent typography, "
            f"and a practical CTA. Keep the subject and text within the platform safe area. "
            f"Do not add unsupported claims or fabricated proof."
        )
