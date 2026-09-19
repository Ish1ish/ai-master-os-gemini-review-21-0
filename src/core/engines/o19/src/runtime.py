from .engine import RealSalesEngine

class O19Runtime:
    def __init__(self): self.engine=RealSalesEngine()
    def run(self,product_output,brand_output,marketing_output):
        return self.engine.build(product_output,brand_output,marketing_output)
