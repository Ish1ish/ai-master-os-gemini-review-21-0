import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TEST=ROOT/"src/ui/tests/test_o46_golden_experience.py"
proc=subprocess.run([sys.executable,str(TEST)],cwd=ROOT,text=True)
if proc.returncode: raise SystemExit(proc.returncode)
print("UI10_O46_GOLDEN_EXPERIENCE_PASS")
print(json.dumps({"release":"UI10-O46","status":"PASS","checks":{
"golden_experience_present":True,"nine_stage_journey":True,"backend_derived":True,"approval_state_visible":True,"outcome_learning_visible":True,"explainability_hook":True,"read_only_surface":True,"responsive":True,"reduced_motion":True,"targeted_tests":True
},"path":"UI1-UI9 unified experience -> full product golden experience -> end-to-end visual QA"},ensure_ascii=False))
