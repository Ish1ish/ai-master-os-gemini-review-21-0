from __future__ import annotations
import importlib, json, os, subprocess, sys, traceback

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_root = os.path.join(ROOT, "src")
sys.path.insert(0, src_root)
checks: dict[str, bool] = {}
notes: list[str] = []

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

def read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

auth_src = read_text(required_modules["auth"][1])
identity_src = read_text(required_modules["identity"][1])
boundary_src = read_text(required_modules["security_boundary"][1])
drill_src = read_text(required_modules["abuse_drill"][1])
service_src = read_text(os.path.join(src_root, "core", "src", "service.py"))

# Actual O36 contract: issue_token() creates the signed token; authenticate() delegates
# to _authenticate_token(), which verifies the signature and rejects invalid_token_signature.
checks["signed_bearer_auth_contract"] = all(token in auth_src for token in ("build_default_production_authenticator", "authenticate"))
checks["identity_token_issue_verify_contract"] = all(token in identity_src for token in ("def issue_token", "def _authenticate_token", "invalid_token_signature", "token.split"))
checks["security_boundary_fail_closed_contract"] = all(token in boundary_src for token in ("class ProductionSecurityBoundary", "authenticated", "token_present", "failures"))
checks["service_auth_boundary_present"] = all(token in service_src for token in ("authenticator", "def submit", "def execute"))

# Tenant evidence can live in the dedicated adversarial drill and any tenant/isolation source
# under the unified core/runtime tree. Do not require a specific module name.
all_src = []
for root_dir in (os.path.join(src_root, "core"), os.path.join(src_root, "unified_runtime")):
    if not os.path.isdir(root_dir):
        continue
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for filename in filenames:
            if filename.endswith(".py"):
                all_src.append(read_text(os.path.join(dirpath, filename)).lower())
all_src_text = "\n".join(all_src)
checks["tenant_security_reference_present"] = (
    "tenant_id" in drill_src.lower()
    and any(marker in all_src_text for marker in ("tenant_id", "cross-tenant", "tenant isolation", "resource isolation", "tenant-aware"))
)

try:
    result = mods["abuse_drill"].run_security_abuse_drill()
    for key, value in result.items():
        checks[f"drill_{key}"] = bool(value)
except Exception:
    checks["drill_execution"] = False
    notes.append(traceback.format_exc(limit=3))
    result = {}

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
    "release": "O39-S43.2",
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
