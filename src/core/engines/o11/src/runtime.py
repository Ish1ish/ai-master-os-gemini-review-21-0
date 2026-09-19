from .engine import RealMarketIntelligenceEngine


class O11Runtime:
    def __init__(self, search_provider=None):
        self.engine = RealMarketIntelligenceEngine(search_provider=search_provider)

    def run(self, request: str, goal: str = "", dimensions=None):
        return self.engine.research(request, goal=goal, dimensions=dimensions)
