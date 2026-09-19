import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
cmd=[sys.executable, str(ROOT/"src/ui/tests/test_o46_outcome_learning.py")]
proc=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
print(proc.stdout,end="")
if proc.stderr: print(proc.stderr,end="",file=sys.stderr)
if proc.returncode:
    raise SystemExit(proc.returncode)
print("UI7_O46_OUTCOME_LEARNING_PASS")
print(json.dumps({
  "release":"UI7-O46",
  "status":"PASS",
  "checks":{
    "outcome_learning_center":True,
    "backend_learning_endpoint":True,
    "outcome_surface":True,
    "learning_surface":True,
    "adaptation_surface":True,
    "next_decision_surface":True,
    "explainability":True,
    "read_only":True,
    "rtl_responsive":True,
    "targeted_tests":True
  },
  "path":"experience contract -> outcome -> learning -> strategy adaptation -> governed next decision"
}))
