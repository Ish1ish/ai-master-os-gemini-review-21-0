from .definition import ProductDefinitionBuilder
from .architecture import ProductArchitectureBuilder
from .features import FeaturePrioritizer
from .content_architecture import ProductContentBuilder
from .launch import LaunchReadiness
from .qa import validate_product_output

class RealProductEngine:
    def __init__(self):
        self.definition=ProductDefinitionBuilder()
        self.architecture=ProductArchitectureBuilder()
        self.features=FeaturePrioritizer()
        self.content=ProductContentBuilder()
        self.launch=LaunchReadiness()

    def build(self,strategy_output,audience="",constraints=None):
        constraints=list(constraints or [])
        idea=strategy_output.get("idea",{})
        strategy=strategy_output.get("strategy",{})
        product_handoff = strategy_output.get("product_handoff", {})
        strategy_for_product = dict(strategy)
        strategy_for_product["product_handoff"] = product_handoff
        definition=self.definition.build(strategy_for_product,idea,audience,constraints)
        architecture=self.architecture.build(definition,strategy)
        features=self.features.prioritize(architecture["modules"],strategy)
        content=self.content.build(definition,architecture)
        launch=self.launch.build(definition,architecture,features)
        out={
            "status":"DRAFT","engine_id":"E-05","engine_version":"O14-v1.0",
            "product_handoff":product_handoff,
            "product_definition":definition,"architecture":architecture,
            "features":features,"content_architecture":content,
            "launch_readiness":launch,
        }
        qa=validate_product_output(out)
        out["qa"]=qa
        out["status"]="COMPLETE" if qa["status"]=="PASS" else "FAILED"
        return out
