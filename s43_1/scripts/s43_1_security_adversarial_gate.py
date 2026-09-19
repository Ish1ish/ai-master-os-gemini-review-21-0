from __future__ import annotations
import importlib, json, os, subprocess, sys, traceback

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_root = os.path.join(ROOT, "src")
sys.path.insert(0, src_root)
checks: dict[str, bool] = {}
notes: list[str] = []

# Required production security modules from the current unified workspace contract.
required_modules = {
    "auth": ("core.src.auth", os.path.join(src_root, "core", "src", "auth.py")),
    "identity": ("core.src.identity", os.path.join(src_root, "core", "src", "identity.py")),
    "security_boundary": ("unified_runtime.security_boundary", os.path.join(src_root, "unified_runtime", "security_boundary.py")),
    "abuse_drill": ("core.src.security_abuse_drill", os.path.join(src_root, "core", "src", "security_abuse_drill.py")),
}
mods = {}
for key, (modname, path) in required_modules.items():
    checks[f"{key}_source_present"] = os.path.isfile(path)
    try:
        mods[key] = importlib.import_module(modname)
        checks[f"{key}_imported"] = True
    except Exception as exc:
        checks[f"{key}_imported"] = False
        notes.append(f"{modname}:{type(exc).__name__}:{exc}")

# Source-contract checks: fail closed if the expected security boundary disappeared.
auth_src = ""
identity_src = ""
boundary_src = ""
service_src = ""
for path, target in [
    (required_modules["auth"][1], "auth"),
    (required_modules["identity"][1], "identity"),
    (required_modules["security_boundary"][1], "boundary"),
    (os.path.join(src_root, "core", "src", "service.py"), "service"),
]:
    try:
        text = open(path, "r", encoding="utf-8").read()
    except Exception:
        text = ""
    if target == "auth": auth_src = text
    elif target == "identity": identity_src = text
    elif target == "boundary": boundary_src = text
    else: service_src = text

checks["signed_bearer_auth_contract"] = all(token in auth_src for token in ("build_default_production_authenticator", "authenticate"))
checks["identity_token_issue_verify_contract"] = (
    "issue_token" in identity_src
    and any(token in identity_src for token in ("_authenticate_token", "authenticate", "verify_token", "verify"))
    and "invalid_token_signature" in identity_src
)
checks["security_boundary_fail_closed_contract"] = all(token in boundary_src for token in ("ProductionSecurityBoundary", "authenticated", "fail"))
checks["service_auth_boundary_present"] = ("authenticator" in service_src and "submit(" in service_src and "execute(" in service_src)
all_src_text = ""
for root_dir in (os.path.join(src_root, "core"), os.path.join(src_root, "unified_runtime"), src_root):
    if not os.path.isdir(root_dir):
        continue
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for filename in filenames:
            if filename.endswith(".py"):
                try:
                    all_src_text += "\n" + open(os.path.join(dirpath, filename), "r", encoding="utf-8").read()
                except Exception:
                    pass
checks["tenant_security_reference_present"] = any(
    x in all_src_text.lower()
    for x in ("tenant_id", "tenant", "cross-tenant", "tenant-aware", "tenant isolation", "resource isolation")
)

# Dependency-free adversarial drill.
try:
    result = mods["abuse_drill"].run_security_abuse_drill()
    for key, value in result.items():
        checks[f"drill_{key}"] = bool(value)
except Exception:
    checks["drill_execution"] = False
    notes.append(traceback.format_exc(limit=3))
    result = {}

# Targeted tests, native Python only.
try:
    p = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tests", "test_s43_security_abuse.py")],
        cwd=ROOT, text=True, capture_output=True, timeout=30
    )
    test_output = (p.stdout + p.stderr).strip()
    checks["targeted_tests"] = p.returncode == 0 and "S43_TARGETED_TESTS_PASS 8/8" in p.stdout
except Exception as exc:
    test_output = f"{type(exc).__name__}: {exc}"
    checks["targeted_tests"] = False

status = "PASS" if checks and all(checks.values()) else "FAIL"
report = {
    "release": "O39-S43.1",
    "status": status,
    "checks": checks,
    "adversarial_metrics": {
        "missing_token_rejected": result.get("missing_token_rejected"),
        "malformed_token_rejected": result.get("malformed_token_rejected"),
        "scope_escalation_denied": result.get("scope_escalation_denied"),
        "cross_tenant_access_denied": result.get("cross_tenant_access_denied"),
        "tenant_owner_mismatch_denied": result.get("tenant_owner_mismatch_denied"),
        "replay_request_blocked": result.get("replay_request_blocked"),
        "valid_scoped_access_allowed": result.get("valid_scoped_access_allowed"),
        "admin_scope_override_explicit": result.get("admin_scope_override_explicit"),
    },
    "targeted_test_output": test_output,
    "external_action_executed": False,
    "memory_write_executed": False,
    "internet_facing_production_approval": False,
    "notes": notes,
}
os.makedirs(os.path.join(ROOT, "staging"), exist_ok=True)
with open(os.path.join(ROOT, "staging", "s43_security_abuse.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
print("S43_SECURITY_ABUSE_" + status)
print(json.dumps(report, indent=2))
