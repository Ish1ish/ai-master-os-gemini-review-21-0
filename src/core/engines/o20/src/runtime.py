from .engine import RealAutomationEngine

class O20Runtime:
    def __init__(self): self.engine=RealAutomationEngine()
    def run(self,process,trigger_spec=None):
        return self.engine.build(process,trigger_spec)
