from .engine import RealContentEngine

class O16Runtime:
    def __init__(self): self.engine=RealContentEngine()
    def run(self,product_output,brand_output,platforms=None,topics_per_pillar=4):
        return self.engine.build(product_output,brand_output,platforms,topics_per_pillar)
