from .engine import RealProductEngine
class O14Runtime:
    def __init__(self): self.engine=RealProductEngine()
    def run(self,strategy_output,audience="",constraints=None):
        return self.engine.build(strategy_output,audience,constraints)
