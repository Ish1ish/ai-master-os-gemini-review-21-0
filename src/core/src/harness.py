import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import json
import time
import traceback
from dataclasses import dataclass, asdict
from typing import Callable, Dict, Any, List


@dataclass
class CheckResult:
    check_id: str
    name: str
    status: str
    duration_ms: float
    details: Dict[str, Any]


class EvaluationHarness:
    def __init__(self):
        self.results: List[CheckResult] = []

    def run_check(self, check_id: str, name: str, fn: Callable[[], Dict[str, Any]]):
        start=time.perf_counter()
        try:
            details=fn()
            status="PASS"
        except AssertionError as exc:
            status="FAIL"
            details={"error":"assertion_failed","message":str(exc)}
        except Exception as exc:
            status="ERROR"
            details={
                "error":type(exc).__name__,
                "message":str(exc),
                "traceback":traceback.format_exc(limit=3),
            }
        duration=(time.perf_counter()-start)*1000
        result=CheckResult(check_id,name,status,duration,details)
        self.results.append(result)
        return result

    def summary(self):
        counts={"PASS":0,"FAIL":0,"ERROR":0}
        for r in self.results:
            counts[r.status]+=1
        return {
            "total":len(self.results),
            "passed":counts["PASS"],
            "failed":counts["FAIL"],
            "errors":counts["ERROR"],
            "release_status":"PASS" if counts["FAIL"]==0 and counts["ERROR"]==0 else "BLOCKED",
        }

    def report(self):
        return {
            "summary":self.summary(),
            "checks":[asdict(r) for r in self.results],
        }
