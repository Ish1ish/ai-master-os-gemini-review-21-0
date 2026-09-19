import json
from src.o35_smoke import run_smoke
out=run_smoke()
print(json.dumps(out,indent=2,ensure_ascii=False))
raise SystemExit(0 if out.get("status")=="COMPLETE" else 1)
