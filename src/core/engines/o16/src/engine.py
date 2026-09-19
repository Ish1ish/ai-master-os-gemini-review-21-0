from .pillars import ContentPillarBuilder
from .topics import TopicGenerator
from .formats import ContentFormatPlanner
from .hooks import HookGenerator
from .copy import CaptionBuilder
from .repurpose import Repurposer
from .qa import validate_content_output


class RealContentEngine:
    def __init__(self):
        self.pillars=ContentPillarBuilder()
        self.topics=TopicGenerator()
        self.formats=ContentFormatPlanner()
        self.hooks=HookGenerator()
        self.captions=CaptionBuilder()
        self.repurposer=Repurposer()

    def build(self, product_output, brand_output,
              platforms=None, topics_per_pillar=4):
        product_handoff = product_output.get("product_to_brand_handoff", {}) or {}
        product_definition=dict(product_output.get("product_definition",{}))
        if product_handoff:
            if product_handoff.get("problem"):
                product_definition["core_problem"] = product_handoff["problem"]
            if product_handoff.get("promise"):
                product_definition["core_promise"] = product_handoff["promise"]
            if product_handoff.get("audience"):
                product_definition["target_audience"] = product_handoff["audience"]
        brand_dna=brand_output.get("brand_dna",{})
        voice=brand_output.get("voice",{})
        brand_voice=voice.get("voice",{})

        pillars=self.pillars.build(product_definition,brand_dna)

        topics=self.topics.generate(
            pillars,
            problem=product_definition.get("core_problem",""),
            promise=product_definition.get("core_promise",""),
            audience=brand_dna.get("audience",product_definition.get("target_audience","")),
            topics_per_pillar=topics_per_pillar,
        )

        formats=self.formats.build(topics,platforms)

        hooks=[]
        captions=[]
        repurposing=[]

        for topic in topics.get("topics",[]):
            hook_pack=self.hooks.generate(topic,{"voice":brand_voice},count=5)
            hooks.append(hook_pack)

            hook=hook_pack["hooks"][0]
            cta="Learn more / take the next practical step."
            caption=self.captions.build(topic,hook,voice,cta)
            captions.append(caption)

            repurposing.append(self.repurposer.build(caption))

        out={
            "status":"DRAFT",
            "engine_id":"E-07",
            "engine_version":"O16-v1.0",
            "pillars":pillars,
            "topics":topics,
            "formats":formats,
            "hooks":hooks,
            "captions":captions,
            "repurposing":repurposing,
            "brand_to_content_handoff": brand_output.get("brand_to_content_handoff", {}),
            "product_to_brand_handoff": product_handoff,
        }

        qa=validate_content_output(out)
        out["qa"]=qa
        out["status"]="COMPLETE" if qa["status"]=="PASS" else "FAILED"
        return out
