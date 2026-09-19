
import importlib
import inspect
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "staging" / "s36_1_provider_adapter_inventory.json"
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

def safe_bool(name):
    return bool(os.getenv(name))

def safe_signature(obj):
    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError):
        return "<signature-unavailable>"

def main():
    result = {
        "release": "O39-S36.1",
        "status": "FAIL",
        "module": "core.src.live_providers",
        "environment_presence": {k: safe_bool(k) for k in ENV_KEYS},
        "module_imported": False,
        "module_file": None,
        "public_callables": [],
        "provider_candidates": {
            "model": [],
            "search": [],
            "other": [],
        },
        "notes": [],
    }

    try:
        mod = importlib.import_module("core.src.live_providers")
    except Exception as exc:
        result["notes"].append(f"import_error:{type(exc).__name__}")
        OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print("S36_1_PROVIDER_ADAPTER_DISCOVERY_FAIL")
        return 1

    result["module_imported"] = True
    result["module_file"] = str(getattr(mod, "__file__", ""))

    for name, obj in sorted(vars(mod).items()):
        if name.startswith("_"):
            continue
        if inspect.isfunction(obj) or inspect.isclass(obj):
            entry = {
                "name": name,
                "kind": "class" if inspect.isclass(obj) else "function",
                "signature": safe_signature(obj),
            }
            result["public_callables"].append(entry)
            low = name.lower()
            if "model" in low or "chat" in low or "completion" in low:
                result["provider_candidates"]["model"].append(name)
            elif "search" in low or "tavily" in low or "retriev" in low:
                result["provider_candidates"]["search"].append(name)
            else:
                result["provider_candidates"]["other"].append(name)

    result["status"] = "PASS"
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("S36_1_PROVIDER_ADAPTER_DISCOVERY_PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
