from time import monotonic
from collections import defaultdict, deque


class RateLimiter:
    """
    In-process sliding-window limiter.
    """

    def __init__(self, max_calls=10, window_seconds=60.0):
        self.max_calls=max_calls
        self.window_seconds=window_seconds
        self.calls=defaultdict(deque)

    def allow(self, key: str):
        now=monotonic()
        q=self.calls[key]
        while q and now-q[0] > self.window_seconds:
            q.popleft()

        if len(q) >= self.max_calls:
            return {"status":"RATE_LIMITED","retry_after_seconds":max(0.0,self.window_seconds-(now-q[0]))}

        q.append(now)
        return {"status":"ALLOW","remaining":self.max_calls-len(q)}
