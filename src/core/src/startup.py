
import os
import sys
from pathlib import Path


def check_python(min_major=3, min_minor=10):
    ok=(sys.version_info.major,sys.version_info.minor) >= (min_major,min_minor)
    return {
        "name":"python",
        "status":"PASS" if ok else "FAIL",
        "version":f"{sys.version_info.major}.{sys.version_info.minor}",
        "minimum":f"{min_major}.{min_minor}",
    }


def check_required_paths(root):
    required=[
        "src",
        "config",
        "scripts",
        "schemas",
        "docs",
    ]
    checks=[]
    for rel in required:
        p=Path(root)/rel
        checks.append({
            "name":f"path:{rel}",
            "status":"PASS" if p.exists() else "FAIL",
        })
    return checks


def check_env_names(production=None):
    production = (os.getenv("AI_OS_ENV", "local").strip().lower() in {"prod", "production"}) if production is None else bool(production)
    names=[
        "AI_OS_MODEL_BASE_URL",
        "AI_OS_MODEL_API_KEY",
        "AI_OS_MODEL_NAME",
        "AI_OS_SEARCH_BASE_URL",
        "AI_OS_SEARCH_API_KEY",
        "AI_OS_MEMORY_DB_PATH",
        "AI_OS_AUDIT_DB_PATH",
    ]
    secret_name = "AI_OS_IDENTITY_SIGNING_SECRET"
    required = names + ([secret_name, "AI_OS_ENV"] if production else [])
    missing = [n for n in required if not os.getenv(n)]
    return {
        "name":"production_env",
        "status":"CONFIGURED" if not missing else ("FAIL" if production else "NOT_CONFIGURED"),
        "required_names":required,
        "missing":missing,
        "production":production,
    }


def run_startup_checks(root):
    checks=[check_python()]
    checks.extend(check_required_paths(root))
    checks.append(check_env_names())
    failures=sum(1 for c in checks if c.get("status")=="FAIL")
    return {
        "status":"PASS" if failures==0 else "FAIL",
        "checks":checks,
    }
