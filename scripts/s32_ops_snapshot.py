from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "staging" / "ops_snapshot"

SAFE_FILES = [
    ROOT / "config" / "o39_operations_manifest.json",
    ROOT / "tools" / "caddy" / "Caddyfile",
    ROOT / "scripts" / "windows_s21_staging_start.cmd",
    ROOT / "scripts" / "windows_s21_staging_stop.cmd",
    ROOT / "scripts" / "windows_s32_ops_status.cmd",
    ROOT / "scripts" / "windows_s32_ops_start.cmd",
    ROOT / "scripts" / "windows_s32_ops_stop.cmd",
    ROOT / "scripts" / "windows_s32_ops_snapshot.cmd",
]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def run(command: str) -> str:
    p = subprocess.run(command, cwd=ROOT, shell=True, capture_output=True, text=True)
    return (p.stdout + p.stderr).strip()

OUT.mkdir(parents=True, exist_ok=True)

data = {
    "release": "O39-S32",
    "workspace": str(ROOT),
    "platform": platform.platform(),
    "python": platform.python_version(),
    "secret_safe": True,
    "network": {
        "8091": run("netstat -ano | findstr \":8091\" | findstr \"LISTENING\""),
        "8443": run("netstat -ano | findstr \":8443\" | findstr \"LISTENING\""),
    },
    "required_file_hashes": {},
}

for path in SAFE_FILES:
    if path.exists():
        data["required_file_hashes"][str(path.relative_to(ROOT))] = sha256(path)

OUT.joinpath("snapshot.json").write_text(
    json.dumps(data, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
print("S32_OPS_SNAPSHOT_CREATED")
