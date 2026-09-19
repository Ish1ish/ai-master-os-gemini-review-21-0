#!/usr/bin/env python3
"""AI Master OS O38 go-live preflight and evidence gate.

The gate never prints secret values. It performs only safe, read-only checks,
local SQLite backup/restore drills, provider connectivity when explicitly
configured, and rollback artifact verification. Network/firewall/TLS checks
that require the target infrastructure are reported as MANUAL rather than
being guessed from the local machine.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PROVIDER = [
    "AI_OS_MODEL_BASE_URL",
    "AI_OS_MODEL_API_KEY",
    "AI_OS_MODEL_NAME",
    "AI_OS_SEARCH_BASE_URL",
    "AI_OS_SEARCH_API_KEY",
]
REQUIRED_RUNTIME = REQUIRED_PROVIDER + [
    "AI_OS_IDENTITY_SIGNING_SECRET",
    "AI_OS_MEMORY_DB_PATH",
    "AI_OS_AUDIT_DB_PATH",
    "AI_OS_JOBS_DB_PATH",
]


def status(name: str, state: str, detail: str, **extra):
    out = {"name": name, "status": state, "detail": detail}
    out.update(extra)
    return out


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_expected_sha(path: Path) -> str | None:
    candidates = [path.with_suffix(path.suffix + ".sha256"), path.with_suffix(".sha256")]
    for sidecar in candidates:
        if sidecar.exists():
            text = sidecar.read_text(encoding="utf-8", errors="replace").strip()
            m = re.search(r"\b([0-9a-fA-F]{64})\b", text)
            if m:
                return m.group(1).lower()
    return None


def package_check(archive: Path | None):
    manifest = ROOT / "release" / "manifest.json"
    if not manifest.exists():
        return status("package_manifest", "FAIL", "release/manifest.json is missing")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception as exc:
        return status("package_manifest", "FAIL", f"manifest unreadable: {type(exc).__name__}")
    release = str(data.get("release", ""))
    if not release:
        return status("package_manifest", "FAIL", "manifest release is missing")
    if not release.startswith(("O38-", "O39-")):
        return status("package_manifest", "FAIL", f"unsupported release={release!r}")
    if archive is None:
        return status("package_integrity", "MANUAL", "No deployment archive supplied; inspect the exact SHA-256 before rollout")
    if not archive.exists():
        return status("package_integrity", "FAIL", f"archive missing: {archive}")
    actual = sha256(archive)
    expected = parse_expected_sha(archive)
    if expected and actual != expected:
        return status("package_integrity", "FAIL", "archive SHA-256 does not match sidecar", expected_sha256=expected, actual_sha256=actual)
    if not expected:
        return status("package_integrity", "MANUAL", "archive exists but no sidecar checksum was found", actual_sha256=actual)
    return status("package_integrity", "PASS", "archive SHA-256 matches sidecar", sha256=actual)


def secrets_env_check():
    env = os.getenv("AI_OS_ENV", "").strip().lower()
    if env not in {"prod", "production"}:
        return status("production_environment", "FAIL", "AI_OS_ENV must be production")
    missing = [n for n in REQUIRED_RUNTIME if not os.getenv(n)]
    if missing:
        return status("production_environment", "FAIL", "required production variables are missing", missing=missing)
    secret = os.environ["AI_OS_IDENTITY_SIGNING_SECRET"]
    if len(secret.encode("utf-8")) < 16:
        return status("production_secret", "FAIL", "identity signing secret is shorter than 16 bytes")
    insecure_markers = {"REPLACE_WITH_32_PLUS_BYTE_RANDOM_SECRET", "o36-local-development-only-secret", "verification-secret-32-bytes-min"}
    if secret in insecure_markers:
        return status("production_secret", "FAIL", "identity signing secret is a known example/test value")
    url_failures = []
    for key in ("AI_OS_MODEL_BASE_URL", "AI_OS_SEARCH_BASE_URL"):
        parsed = urlparse(os.environ[key])
        if parsed.scheme != "https" or not parsed.netloc:
            url_failures.append(key)
    if url_failures:
        return status("provider_transport", "FAIL", "provider URLs must be HTTPS with a valid host", invalid=url_failures)
    return status("production_environment", "PASS", "required environment is configured; secret values were not printed", secret_bytes=len(secret.encode("utf-8")))


def provider_smoke():
    missing = [n for n in REQUIRED_PROVIDER if not os.getenv(n)]
    if missing:
        return status("staging_provider_smoke", "NOT_READY", "live provider smoke cannot run until provider variables are configured", missing=missing)
    script = ROOT / "scripts" / "staging_provider_smoke.py"
    proc = subprocess.run([sys.executable, str(script)], cwd=ROOT, capture_output=True, text=True, timeout=90)
    combined = (proc.stdout + "\n" + proc.stderr).strip()
    if "STAGING_PROVIDER_SMOKE_PASS" in combined and proc.returncode == 0:
        return status("staging_provider_smoke", "PASS", "model and search provider connectivity succeeded")
    safe_tail = "\n".join(line for line in combined.splitlines() if not any(token in line.lower() for token in ("api_key", "authorization", "secret", "token")))
    return status("staging_provider_smoke", "FAIL", f"provider smoke failed (exit={proc.returncode})", output_tail=safe_tail[-1200:])


def sqlite_drill():
    from scripts.backup_sqlite import backup, verify
    import shutil

    db_envs = [
        ("memory", "AI_OS_MEMORY_DB_PATH"),
        ("audit", "AI_OS_AUDIT_DB_PATH"),
        ("jobs", "AI_OS_JOBS_DB_PATH"),
    ]
    results = []
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for label, env_name in db_envs:
            raw = os.getenv(env_name)
            if not raw:
                results.append(status(f"backup_restore_{label}", "FAIL", f"{env_name} is missing"))
                continue
            src = Path(raw)
            if not src.exists():
                results.append(status(f"backup_restore_{label}", "SKIP", "database does not exist yet; no existing production data to back up"))
                continue
            dst = td / f"{label}.backup.sqlite3"
            restore = td / f"{label}.restore.sqlite3"
            try:
                backup(src, dst)
                if not verify(dst):
                    raise RuntimeError("backup integrity_check failed")
                shutil.copy2(dst, restore)
                if not verify(restore):
                    raise RuntimeError("restore integrity_check failed")
                results.append(status(f"backup_restore_{label}", "PASS", "backup and isolated restore integrity checks passed"))
            except Exception as exc:
                results.append(status(f"backup_restore_{label}", "FAIL", f"{type(exc).__name__}: {exc}"))
    return results


def rollback_check(prior_archive: Path | None):
    if prior_archive is None:
        return status("rollback_artifact", "MANUAL", "Supply --prior-archive to verify the previous production release artifact")
    if not prior_archive.exists():
        return status("rollback_artifact", "FAIL", f"prior archive missing: {prior_archive}")
    digest = sha256(prior_archive)
    expected = parse_expected_sha(prior_archive)
    if expected and expected != digest:
        return status("rollback_artifact", "FAIL", "prior archive checksum mismatch", expected_sha256=expected, actual_sha256=digest)
    return status("rollback_artifact", "PASS" if expected else "MANUAL", "prior release artifact is available" + (" and checksum verified" if expected else "; checksum sidecar missing"), sha256=digest)


def static_deployment_check():
    checks = []
    api_unit = (ROOT / "deploy" / "o38-api.service.example").read_text(encoding="utf-8")
    nginx = (ROOT / "deploy" / "o38-nginx.example.conf").read_text(encoding="utf-8")
    checks.append(status("loopback_api", "PASS" if "--host 127.0.0.1" in api_unit else "FAIL", "API example uses loopback binding"))
    checks.append(status("tls_edge", "PASS" if "listen 443 ssl" in nginx and "proxy_pass http://127.0.0.1:8080" in nginx else "FAIL", "TLS reverse-proxy example is present"))
    checks.append(status("public_8080_guard", "FAIL" if re.search(r"0\.0\.0\.0:8080|listen\s+8080", nginx, re.I) else "PASS", "nginx example does not expose application port directly"))
    return checks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", type=Path, help="exact O38 deployment archive")
    ap.add_argument("--prior-archive", type=Path, help="previous production release archive for rollback verification")
    ap.add_argument("--skip-provider", action="store_true", help="do not call external staging providers")
    args = ap.parse_args()
    archive = args.archive if args.archive and str(args.archive) else None
    prior_archive = args.prior_archive if args.prior_archive and str(args.prior_archive) else None

    results = [package_check(archive)]
    env_result = secrets_env_check()
    results.append(env_result)
    results.extend(static_deployment_check())
    results.append(rollback_check(prior_archive))
    if args.skip_provider:
        results.append(status("staging_provider_smoke", "MANUAL", "provider smoke intentionally skipped"))
    else:
        results.append(provider_smoke())
    # Persistence drill is meaningful only when production DB paths are configured.
    if os.getenv("AI_OS_ENV", "").strip().lower() in {"prod", "production"} and not any(r["name"] == "production_environment" and r["status"] == "FAIL" for r in results):
        try:
            results.extend(sqlite_drill())
        except Exception as exc:
            results.append(status("backup_restore", "FAIL", f"sqlite drill failed: {type(exc).__name__}: {exc}"))
    else:
        results.append(status("backup_restore", "BLOCKED", "production environment is not configured; no database drill attempted"))

    manual = [r for r in results if r["status"] in {"MANUAL", "NOT_READY", "SKIP", "BLOCKED"}]
    failed = [r for r in results if r["status"] == "FAIL"]
    if failed:
        overall = "NOT_READY"
    elif manual:
        overall = "CONDITIONAL"
    else:
        overall = "READY"

    report = {
        "product": "AI Master OS",
        "release": json.loads((ROOT / "release" / "manifest.json").read_text(encoding="utf-8")).get("release"),
        "gate": "GO_LIVE_VALIDATION",
        "overall": overall,
        "results": results,
        "note": "Infrastructure-dependent checks (real firewall reachability, approved TLS certificate, operator rollback execution) must be evidenced on the target environment; this script does not guess them.",
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if overall == "NOT_READY":
        return 2
    if overall == "CONDITIONAL":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
