from .dna import BrandDNABuilder
from .positioning import BrandPositioningBuilder
from .messaging import MessagingBuilder
from .voice import BrandVoiceBuilder
from .naming import NamingDirectionBuilder
from .visual import VisualDirectionBuilder
from .qa import validate_brand_output


class RealBrandEngine:
    def __init__(self):
        self.dna=BrandDNABuilder()
        self.positioning=BrandPositioningBuilder()
        self.messaging=MessagingBuilder()
        self.voice=BrandVoiceBuilder()
        self.naming=NamingDirectionBuilder()
        self.visual=VisualDirectionBuilder()

    def build(self, strategy_output, audience="", name_candidates=None):
        product_handoff = strategy_output.get("product_to_brand_handoff", {}) or {}
        product_definition = dict(strategy_output.get("product_definition", {}))
        if product_handoff:
            if product_handoff.get("problem"):
                product_definition["core_problem"] = product_handoff["problem"]
            if product_handoff.get("promise"):
                product_definition["core_promise"] = product_handoff["promise"]
            if product_handoff.get("audience"):
                product_definition["target_audience"] = product_handoff["audience"]
        strategy = strategy_output.get("strategy", {})

        dna=self.dna.build(product_definition,strategy,audience)
        positioning=self.positioning.build(product_definition,strategy,dna)
        messaging=self.messaging.build(dna,positioning)
        voice=self.voice.build(dna)
        naming=self.naming.build(dna,strategy,name_candidates)
        visual=self.visual.build(dna,positioning)

        out={
            "status":"DRAFT",
            "engine_id":"E-06",
            "engine_version":"O15-v1.0",
            "brand_dna":dna,
            "positioning":positioning,
            "messaging":messaging,
            "voice":voice,
            "naming":naming,
            "visual_direction":visual,
        }
        qa=validate_brand_output(out)
        out["qa"]=qa
        out["status"]="COMPLETE" if qa["status"]=="PASS" else "FAILED"
        return out
