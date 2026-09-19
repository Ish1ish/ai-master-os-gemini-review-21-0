from .engine import RealAnalyticsEngine
class O21Runtime:
    def __init__(self): self.engine=RealAnalyticsEngine()
    def run(self,raw_events,funnel_stages,experiment_inputs=None,revenue=0.0,customers=0):
        return self.engine.analyze(raw_events,funnel_stages,experiment_inputs,revenue,customers)
