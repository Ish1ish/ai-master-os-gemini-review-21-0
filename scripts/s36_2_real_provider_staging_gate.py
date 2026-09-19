
import hashlib
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "staging" / "s36_2_real_provider_staging.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

ENV_KEYS = (
    "AI_OS_ENV",
    "AI_OS_MODEL_BASE_URL",
    "AI_OS_MODEL_API_KEY",
    "AI_OS_MODEL_NAME",
    "AI_OS_SEARCH_BASE_URL",
    "AI_OS_SEARCH_API_KEY",
    "AI_OS_REQUEST_TIMEOUT_S",
)

def present(name):
    return bool(os.getenv(name))

def safe_shape(value):
    if isinstance(value, dict):
        return {
            "type": "dict",
            "keys": sorted(str(k) for k in value.keys()),
            "status": value.get("status") if isinstance(value.get("status"), str) else None,
        }
    if isinstance(value, list):
        return {"type": "list", "length": len(value)}
    if value is None:
        return {"type": "none"}
    return {"type": type(value).__name__}

def safe_error(exc):
    return {
        "type": type(exc).__name__,
        "message_class": type(exc).__name__,
    }

def digest_value(value):
    try:
        raw = repr(value).encode("utf-8", errors="replace")
    except Exception:
        raw = b"<unrepr>"
    return hashlib.sha256(raw).hexdigest()

def configured():
    model = all(present(k) for k in (
        "AI_OS_MODEL_BASE_URL",
        "AI_OS_MODEL_API_KEY",
        "AI_OS_MODEL_NAME",
    ))
    search = all(present(k) for k in (
        "AI_OS_SEARCH_BASE_URL",
        "AI_OS_SEARCH_API_KEY",
    ))
    return model, search

def run():
    result = {
        "release": "O39-S36.2",
        "status": "FAIL",
        "provider_module": "core.src.live_providers",
        "environment_presence": {k: present(k) for k in ENV_KEYS},
        "configuration": {
            "model_configured": False,
            "search_configured": False,
        },
        "provider_configuration_status": None,
        "model": {
            "attempted": False,
            "status": "NOT_RUN",
        },
        "search": {
            "attempted": False,
            "status": "NOT_RUN",
        },
        "external_action_executed": False,
        "memory_write_executed": False,
        "notes": [],
    }

    try:
        from core.src import live_providers
    except Exception as exc:
        result["notes"].append({"stage": "import", "error": safe_error(exc)})
        OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print("S36_2_REAL_PROVIDER_STAGING_FAIL")
        return 1

    model_ok, search_ok = configured()
    result["configuration"]["model_configured"] = model_ok
    result["configuration"]["search_configured"] = search_ok

    try:
        cfg = live_providers.provider_configuration_status()
        result["provider_configuration_status"] = safe_shape(cfg)
    except Exception as exc:
        result["notes"].append({"stage": "configuration_status", "error": safe_error(exc)})

    if not (model_ok and search_ok):
        result["notes"].append({
            "stage": "preflight",
            "reason": "required_provider_environment_not_configured",
        })
        OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print("S36_2_REAL_PROVIDER_STAGING_NOT_CONFIGURED")
        return 2

    model_prompt = (
        "AI Master OS staging smoke test. "
        "Reply with exactly: PROVIDER_SMOKE_OK"
    )
    search_query = "OpenAI"

    try:
        result["model"]["attempted"] = True
        started = time.perf_counter()
        value = live_providers.model_provider(model_prompt)
        result["model"]["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
        result["model"]["result_shape"] = safe_shape(value)
        result["model"]["result_sha256"] = digest_value(value)
        model_text = value.get("text") if isinstance(value, dict) else None
        model_has_identity = isinstance(value, dict) and bool(value.get("provider")) and bool(value.get("model"))
        model_ok = (
            isinstance(value, dict)
            and model_has_identity
            and isinstance(model_text, str)
            and model_text.strip() == "PROVIDER_SMOKE_OK"
        )
        result["model"]["status"] = "PASS" if model_ok else "FAIL_CONTRACT"
    except Exception as exc:
        result["model"]["status"] = "FAIL"
        result["model"]["error"] = safe_error(exc)

    try:
        result["search"]["attempted"] = True
        started = time.perf_counter()
        value = live_providers.search_provider(search_query)
        result["search"]["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
        result["search"]["result_shape"] = safe_shape(value)
        result["search"]["result_sha256"] = digest_value(value)
        search_results = value.get("results") if isinstance(value, dict) else None
        search_ok = (
            isinstance(value, dict)
            and isinstance(search_results, list)
            and len(search_results) > 0
        )
        result["search"]["status"] = "PASS" if search_ok else "FAIL_CONTRACT"
    except Exception as exc:
        result["search"]["status"] = "FAIL"
        result["search"]["error"] = safe_error(exc)

    result["status"] = (
        "PASS"
        if result["model"]["status"] == "PASS"
        and result["search"]["status"] == "PASS"
        and not result["external_action_executed"]
        and not result["memory_write_executed"]
        else "FAIL"
    )

    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("S36_2_REAL_PROVIDER_STAGING_PASS" if result["status"] == "PASS" else "S36_2_REAL_PROVIDER_STAGING_FAIL")
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(run())
