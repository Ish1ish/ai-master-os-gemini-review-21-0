class DaemonHealth:
    def check(self, daemon):
        return {
            "status":"HEALTHY" if daemon.running else "STOPPED",
            "worker_id":daemon.worker_id,
            "running":daemon.running,
            "last_result":daemon.last_result,
        }
