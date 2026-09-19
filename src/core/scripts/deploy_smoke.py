import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from src.runtime import O31Runtime

out=O31Runtime(root=ROOT).deploy_smoke()
print(json.dumps(out,indent=2,ensure_ascii=False))
if out["status"]!="COMPLETE":
    raise SystemExit(1)
