from .engine import RealMarketingEngine

class O18Runtime:
    def __init__(self): self.engine=RealMarketingEngine()
    def run(self,product_output,brand_output,market_report=None,content_output=None,objective="validate acquisition"):
        return self.engine.build(product_output,brand_output,market_report,content_output,objective)
