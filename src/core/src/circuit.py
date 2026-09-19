from time import monotonic


class CircuitBreaker:
    STATES={"CLOSED","OPEN","HALF_OPEN"}

    def __init__(self, failure_threshold=3, recovery_seconds=30.0):
        self.failure_threshold=failure_threshold
        self.recovery_seconds=recovery_seconds
        self.failures=0
        self.state="CLOSED"
        self.opened_at=None

    def before_call(self):
        if self.state=="OPEN":
            if monotonic()-self.opened_at >= self.recovery_seconds:
                self.state="HALF_OPEN"
            else:
                return {"status":"BLOCK","state":"OPEN"}
        return {"status":"ALLOW","state":self.state}

    def record_success(self):
        self.failures=0
        self.state="CLOSED"
        self.opened_at=None

    def record_failure(self):
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.state="OPEN"
            self.opened_at=monotonic()

    def snapshot(self):
        return {"state":self.state,"failures":self.failures}
