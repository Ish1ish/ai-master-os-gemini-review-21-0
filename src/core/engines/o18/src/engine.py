from .audience import AudiencePlanner
from .offer import OfferBuilder
from .funnel import FunnelBuilder
from .channels import ChannelPlanner
from .campaign import CampaignBuilder
from .experiments import MarketingExperimentPlanner
from .metrics import MarketingMetrics
from .qa import validate_marketing_output


class RealMarketingEngine:
    def __init__(self):
        self.audience = AudiencePlanner()
        self.offer = OfferBuilder()
        self.funnel = FunnelBuilder()
        self.channels = ChannelPlanner()
        self.campaign = CampaignBuilder()
        self.experiments = MarketingExperimentPlanner()
        self.metrics = MarketingMetrics()

    def build(self, product_output, brand_output,
              market_report=None, content_output=None,
              objective="validate acquisition"):
        product_handoff = product_output.get("product_to_brand_handoff", {}) or {}
        product_def = dict(product_output.get("product_definition", {}))
        if product_handoff:
            if product_handoff.get("problem"):
                product_def["core_problem"] = product_handoff["problem"]
            if product_handoff.get("promise"):
                product_def["core_promise"] = product_handoff["promise"]
            if product_handoff.get("audience"):
                product_def["target_audience"] = product_handoff["audience"]
        strategy = product_output.get("strategy", {})
        brand_dna = brand_output.get("brand_dna", {})

        audience = self.audience.build(product_def, market_report)
        offer = self.offer.build(product_def, strategy)
        funnel = self.funnel.build(audience, offer, content_output)
        channels = self.channels.build(audience, objective)
        campaign = self.campaign.build(offer, funnel, channels, content_output)
        experiments = self.experiments.build(campaign)
        metrics = self.metrics.build(funnel)

        out = {
            "status":"DRAFT",
            "engine_id":"E-09",
            "engine_version":"O18-v1.0",
            "brand_context": {
                "audience": brand_dna.get("audience", ""),
                "personality": brand_dna.get("personality", []),
            },
            "audience": audience,
            "offer": offer,
            "funnel": funnel,
            "channels": channels,
            "campaign": campaign,
            "experiments": experiments,
            "metrics": metrics,
            "product_to_brand_handoff": product_handoff,
            "brand_to_content_handoff": brand_output.get("brand_to_content_handoff", {}),
            "visual_to_marketing_handoff": (content_output or {}).get("visual_to_marketing_handoff", {}),
        }

        qa = validate_marketing_output(out)
        out["qa"] = qa
        out["status"] = "COMPLETE" if qa["status"] == "PASS" else "FAILED"
        return out
