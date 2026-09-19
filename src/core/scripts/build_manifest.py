
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from src.release_manifest import create_manifest

manifest=create_manifest()
manifest.write(ROOT/"release"/"manifest.json")
print(json.dumps(manifest.to_dict(),indent=2,ensure_ascii=False))
