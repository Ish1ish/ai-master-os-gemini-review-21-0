class GracefulShutdown:
    def stop(self, supervisor):
        return supervisor.stop(grace_seconds=2.0)
