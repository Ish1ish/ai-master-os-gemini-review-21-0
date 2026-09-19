import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST = ROOT / "src" / "ui" / "tests" / "test_o46_visual_polish.py"

proc = subprocess.run([sys.executable, str(TEST)], cwd=ROOT, text=True)
if proc.returncode != 0:
    raise SystemExit(proc.returncode)

print("UI9_O46_VISUAL_POLISH_PASS")
print(json.dumps({
    "release": "UI9-O46",
    "status": "PASS",
    "checks": {
        "visual_design_tokens": True,
        "motion_system": True,
        "reduced_motion": True,
        "focus_accessibility": True,
        "responsive_polish": True,
        "read_only_surface": True,
        "targeted_tests": True,
    },
    "path": "UI1-UI8 unified experience -> visual system -> motion -> accessibility -> responsive QA",
}, ensure_ascii=False))
