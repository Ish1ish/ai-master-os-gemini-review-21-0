from .engine import RealVisualDesignEngine

class O17Runtime:
    def __init__(self): self.engine=RealVisualDesignEngine()
    def run(self,content_item,brand_output,platform="Instagram"):
        return self.engine.build(content_item,brand_output,platform)
