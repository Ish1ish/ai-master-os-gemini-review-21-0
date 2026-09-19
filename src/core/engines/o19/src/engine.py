from .sales_message import SalesMessageBuilder
from .page_copy import ConversionCopyBuilder
from .qualifier import BuyerQualifier
from .objections import ObjectionHandler
from .followup import FollowUpBuilder
from .expansion import ExpansionBuilder
from .qa import validate_sales_output


class RealSalesEngine:
    def __init__(self):
        self.message=SalesMessageBuilder()
        self.copy=ConversionCopyBuilder()
        self.qualifier=BuyerQualifier()
        self.objections=ObjectionHandler()
        self.followup=FollowUpBuilder()
        self.expansion=ExpansionBuilder()

    def build(self, product_output, brand_output, marketing_output):
        marketing_handoff = marketing_output.get("marketing_to_sales_handoff", {}) or {}
        product_definition=product_output.get("product_definition",{})
        strategy=product_output.get("strategy",{})
        brand=brand_output
        audience=marketing_output.get("audience",{})
        offer=marketing_output.get("offer",{})

        sales_message=self.message.build(product_definition,brand,offer,audience)
        conversion_copy=self.copy.build(product_definition,brand,offer,audience)
        qualification=self.qualifier.build(product_definition,audience)
        objections=self.objections.build()
        follow_up=self.followup.build(offer,audience)
        expansion=self.expansion.build(product_definition,offer)

        out={
            "status":"DRAFT",
            "engine_id":"E-10",
            "engine_version":"O19-v1.0",
            "sales_message":sales_message,
            "conversion_copy":conversion_copy,
            "qualification":qualification,
            "objections":objections,
            "follow_up":follow_up,
            "expansion":expansion,
            "marketing_to_sales_handoff": marketing_handoff,
        }

        qa=validate_sales_output(out)
        out["qa"]=qa
        out["status"]="COMPLETE" if qa["status"]=="PASS" else "FAILED"
        return out
