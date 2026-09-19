from .engine import RealBrandEngine

class O15Runtime:
    def __init__(self): self.engine=RealBrandEngine()
    def run(self,strategy_output,audience="",name_candidates=None):
        return self.engine.build(strategy_output,audience,name_candidates)
