import time


class RetryPolicy:
    def __init__(self, max_attempts=3, base_delay=0.05, backoff_factor=2.0):
        self.max_attempts=max_attempts
        self.base_delay=base_delay
        self.backoff_factor=backoff_factor

    def run(self, operation):
        attempts=0
        last_error=None

        while attempts < self.max_attempts:
            attempts += 1
            try:
                result=operation()
                return {
                    "status":"SUCCESS",
                    "attempts":attempts,
                    "result":result,
                }
            except Exception as exc:
                last_error=exc
                if attempts < self.max_attempts:
                    time.sleep(self.base_delay*(self.backoff_factor**(attempts-1)))

        return {
            "status":"FAILED",
            "attempts":attempts,
            "error":str(last_error),
        }
