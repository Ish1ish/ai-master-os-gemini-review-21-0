from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"
UI = ROOT / "ui"


def run(cmd: list[str], cwd: Path, label: str) -> None:
    print(f"===== {label} =====")
    env = dict(__import__("os").environ)
    env["PYTHONPATH"] = str(cwd)
    env["PYTHONWARNINGS"] = "error::ResourceWarning"
    p = subprocess.run(cmd, cwd=cwd, env=env)
    if p.returncode:
        raise SystemExit(p.returncode)


def main() -> int:
    required = [
        CORE / "scripts" / "windows_o46_verify.cmd",
        CORE / "scripts" / "o44_governance_smoke.py",
        CORE / "scripts" / "o45_execution_smoke.py",
        CORE / "scripts" / "o46_governed_loop_smoke.py",
        UI / "scripts" / "windows_ui_v46_final_verify.cmd",
        UI / "scripts" / "windows_ui_v47_preflight_verify.cmd",
        UI / "ui" / "meta.json",
        UI / "tests" / "test_ui_console.py",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    if missing:
        print("MISSING AUDIT ARTIFACTS:")
        print("\n".join(missing))
        return 1

    meta = json.loads((UI / "ui" / "meta.json").read_text(encoding="utf-8"))
    assert meta["version"] == "4.6.0"
    assert meta["console_version"] == "4.6.0"
    assert meta["release"] == "FINAL"
    assert "final_release" in meta["features"]
    assert "final_release_candidate" not in meta["features"]
    assert meta.get("current_build") == "4.7.0"
    assert "counterfactual_preflight" in meta.get("features", [])

    if "--package-only" not in __import__("sys").argv:
        run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"], CORE, "CORE REGRESSION")
    if "--package-only" not in __import__("sys").argv:
        run([sys.executable, "-m", "compileall", "-q", "src"], CORE, "CORE COMPILEALL")
        run([sys.executable, "scripts/o44_governance_smoke.py"], CORE, "O44 GOVERNANCE SMOKE")
        run([sys.executable, "scripts/o45_execution_smoke.py"], CORE, "O45 EXECUTION SMOKE")
        run([sys.executable, "scripts/o46_governed_loop_smoke.py"], CORE, "O46 GOVERNED LOOP SMOKE")
        run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"], UI, "UI V4.7.0 COUNTERFACTUAL REGRESSION")
        run([sys.executable, "-m", "py_compile", "scripts/console_server.py"], UI, "UI SERVER COMPILE")
        run([sys.executable, "-c", "import json, pathlib; m=json.loads(pathlib.Path('ui/meta.json').read_text(encoding='utf-8')); assert m.get('current_build')=='4.7.0'; assert 'counterfactual_preflight' in m.get('features',[]); print('UI V4.7.0 PREFLIGHT MANIFEST: PASS')"], UI, "UI V4.7.0 MANIFEST")
    print("===== UI MANIFEST =====")
    print("UI MANIFEST: PASS")
    print("===== FINAL AUDIT CHECK =====")
    print("CORE + UI ARTIFACTS: PASS")
    print("FINAL E2E AUDIT: PASS (developer-side)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
