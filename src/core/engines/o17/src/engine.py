from .brief import VisualBriefBuilder
from .layout import LayoutPlanner
from .assets import AssetSpecBuilder
from .prompts import VisualPromptBuilder
from .qa import validate_visual_output


class RealVisualDesignEngine:
    def __init__(self):
        self.brief = VisualBriefBuilder()
        self.layout = LayoutPlanner()
        self.assets = AssetSpecBuilder()
        self.prompts = VisualPromptBuilder()

    def build(self, content_item, brand_output, platform="Instagram"):
        handoff = content_item.get("content_to_visual_handoff", {}) if isinstance(content_item, dict) else {}
        if handoff:
            content_item = dict(content_item)
            content_item.setdefault("topic", handoff.get("topic", ""))
            content_item.setdefault("objective", handoff.get("objective", ""))
        brief = self.brief.build(content_item, brand_output, platform)
        layout = self.layout.build(brief)
        asset_spec = self.assets.build(brief, layout)
        image_prompt = self.prompts.image_prompt(brief, layout)
        video_prompt = self.prompts.video_prompt(brief, layout)

        out = {
            "status":"DRAFT",
            "engine_id":"E-08",
            "engine_version":"O17-v1.0",
            "visual_brief":brief,
            "layout":layout,
            "asset_spec":asset_spec,
            "image_prompt":image_prompt,
            "video_prompt":video_prompt,
            "content_to_visual_handoff": handoff,
        }

        qa=validate_visual_output(out)
        out["qa"]=qa
        out["status"]="COMPLETE" if qa["status"]=="PASS" else "FAILED"
        return out
