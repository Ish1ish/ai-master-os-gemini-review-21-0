
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from src.migrations import init_all

print(json.dumps(init_all(ROOT/"data"),indent=2,ensure_ascii=False))
