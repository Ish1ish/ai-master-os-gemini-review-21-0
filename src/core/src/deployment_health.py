from .health import HealthCheck


class DeploymentHealth:
    def __init__(self):
        self.health=HealthCheck()

    def check(self, components):
        return self.health.check(components)

    def smoke(self, supervisor):
        h=supervisor.health()
        return {
            "status":"PASS" if h["status"]=="HEALTHY" else "FAIL",
            "health":h,
        }
