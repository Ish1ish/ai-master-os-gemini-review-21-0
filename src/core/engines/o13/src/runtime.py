from .engine import RealStrategyEngine
class O13Runtime:
    def __init__(self): self.engine=RealStrategyEngine()
    def run(self,idea,market_report,goal="",constraints=None):
        return self.engine.build(idea,market_report,goal,constraints)
