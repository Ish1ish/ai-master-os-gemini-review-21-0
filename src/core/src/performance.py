import time


class PerformanceSmoke:
    def run(self, fn, max_ms=5000):
        start=time.perf_counter()
        result=fn()
        elapsed=(time.perf_counter()-start)*1000
        return {
            "status":"PASS" if elapsed <= max_ms else "FAIL",
            "elapsed_ms":elapsed,
            "max_ms":max_ms,
            "result_status":result.get("status"),
        }
