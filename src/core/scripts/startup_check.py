
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from src.startup import run_startup_checks

print(json.dumps(run_startup_checks(ROOT),indent=2,ensure_ascii=False))
