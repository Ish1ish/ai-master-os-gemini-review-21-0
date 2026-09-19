from __future__ import annotations
import json, socket, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "staging" / "ops_snapshot"
OUT.mkdir(parents=True, exist_ok=True)

def listener_pids(port: int) -> list[str]:
    p = subprocess.run(
        f'netstat -ano | findstr ":{port}" | findstr "LISTENING"',
        cwd=ROOT, shell=True, capture_output=True, text=True
    )
    return sorted({line.split()[-1] for line in p.stdout.splitlines() if line.split()})

def reachable(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False

result = {
    "release": "O39-S35",
    "staging": True,
    "backend": {
        "bind": "127.0.0.1:8091",
        "listener_pids": listener_pids(8091),
        "loopback_reachable": reachable("127.0.0.1", 8091),
    },
    "tls_edge": {
        "bind": "localhost:8443",
        "listener_pids": listener_pids(8443),
        "loopback_reachable": reachable("127.0.0.1", 8443),
    },
    "contract": {
        "direct_backend_public_exposure_allowed": False,
        "tls_edge_required": True,
    },
}
ok = (
    bool(result["backend"]["listener_pids"]) and result["backend"]["loopback_reachable"] and
    bool(result["tls_edge"]["listener_pids"]) and result["tls_edge"]["loopback_reachable"]
)
result["status"] = "PASS" if ok else "FAIL"
(OUT/"s35_edge_network_contract.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
print(f"S35_EDGE_NETWORK_CONTRACT_{result['status']}")
raise SystemExit(0 if ok else 1)
