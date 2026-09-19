import json
import sys
from pathlib import Path
from src.evaluator import O29Evaluator
from src.report import write_report

report=O29Evaluator().evaluate()
Path("reports").mkdir(parents=True, exist_ok=True)
write_report("reports/O29_release_evaluation.json",report)
print(json.dumps(report,indent=2,ensure_ascii=False))
summary=report.get("summary", {})
gate=report.get("release_gate", {})
if summary.get("failed", 0) or summary.get("errors", 0) or gate.get("status") == "BLOCKED":
    raise SystemExit(1)
