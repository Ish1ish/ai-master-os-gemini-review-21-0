#!/usr/bin/env python3
"""Read-only production operations snapshot.

No credentials are printed. Provider calls are never made. HTTP checks are local only.
"""
from __future__ import annotations
import argparse, json, os, sqlite3, sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "release" / "manifest.json"
DB_VARS = [
    ("memory", "AI_OS_MEMORY_DB_PATH"),
    ("audit", "AI_OS_AUDIT_DB_PATH"),
    ("jobs", "AI_OS_JOBS_DB_PATH"),
]
SECRET_NAMES = ("API_KEY", "SECRET", "TOKEN", "PASSWORD")


def safe_env_status():
    required = [
        "AI_OS_ENV", "AI_OS_MODEL_BASE_URL", "AI_OS_MODEL_API_KEY", "AI_OS_MODEL_NAME",
        "AI_OS_SEARCH_BASE_URL", "AI_OS_SEARCH_API_KEY", "AI_OS_IDENTITY_SIGNING_SECRET",
        "AI_OS_MEMORY_DB_PATH", "AI_OS_AUDIT_DB_PATH", "AI_OS_JOBS_DB_PATH",
    ]
    missing = [name for name in required if not os.getenv(name)]
    secret_presence = {name: bool(os.getenv(name)) for name in required if any(x in name for x in SECRET_NAMES)}
    return {
        "status": "READY" if not missing and os.getenv("AI_OS_ENV", "").lower() in {"prod", "production"} else "NOT_READY",
        "environment": os.getenv("AI_OS_ENV", ""),
        "missing": missing,
        "secret_presence": secret_presence,
    }


def db_status():
    out = []
    for label, env_name in DB_VARS:
        raw = os.getenv(env_name, "")
        path = Path(raw) if raw else None
        item = {"name": label, "configured": bool(raw), "exists": bool(path and path.exists())}
        if path and path.exists():
            item["size_bytes"] = path.stat().st_size
            try:
                con = sqlite3.connect(str(path))
                row = con.execute("PRAGMA integrity_check").fetchone()
                con.close()
                item["integrity"] = row[0] if row else "unknown"
            except Exception as exc:
                item["integrity"] = f"ERROR:{type(exc).__name__}"
        out.append(item)
    return out


def local_http(base: str, path: str):
    url = base.rstrip("/") + path
    try:
        req = Request(url, method="GET")
        with urlopen(req, timeout=3) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw)
            except Exception:
                payload = {"raw": raw}
            return {"status": "PASS", "http_status": resp.status, "payload": payload}
    except HTTPError as exc:
        return {"status": "FAIL", "http_status": exc.code}
    except URLError as exc:
        return {"status": "NOT_RUNNING", "detail": str(getattr(exc, "reason", exc))}
    except Exception as exc:
        return {"status": "FAIL", "detail": f"{type(exc).__name__}: {exc}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://127.0.0.1:8080")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    report = {
        "product": manifest.get("product"),
        "release": manifest.get("release"),
        "channel": manifest.get("channel"),
        "environment": safe_env_status(),
        "databases": db_status(),
        "local_api": {
            "health": local_http(args.api, "/health"),
            "readiness": local_http(args.api, "/readiness"),
        },
        "provider_calls": "NONE",
        "secrets_printed": False,
        "snapshot_type": "READ_ONLY",
    }
    text=json.dumps(report,indent=2,ensure_ascii=False)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text+"\n",encoding="utf-8")

if __name__ == "__main__":
    main()
