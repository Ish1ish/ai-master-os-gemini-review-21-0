from .engine import RealIdeaEngine


class O12Runtime:
    def __init__(self):
        self.engine = RealIdeaEngine()

    def run(self, market_report, audience="", constraints=None, max_ideas=20):
        return self.engine.build(
            market_report=market_report,
            audience=audience,
            constraints=constraints,
            max_ideas=max_ideas,
        )
