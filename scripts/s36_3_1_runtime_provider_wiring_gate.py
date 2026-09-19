
import hashlib
import inspect
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "staging" / "s36_3_runtime_provider_wiring.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

def safe_hash(text):
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()

def contains_identity(obj, target, depth=0, max_depth=4, seen=None):
    if obj is target:
        return True
    if depth >= max_depth:
        return False
    if seen is None:
        seen = set()
    marker = id(obj)
    if marker in seen:
        return False
    seen.add(marker)

    if callable(obj):
        if obj is target:
            return True

    if isinstance(obj, dict):
        for value in obj.values():
            if contains_identity(value, target, depth + 1, max_depth, seen):
                return True
        return False

    if isinstance(obj, (list, tuple, set, frozenset)):
        for value in obj:
            if contains_identity(value, target, depth + 1, max_depth, seen):
                return True
        return False

    try:
        values = vars(obj)
    except TypeError:
        return False

    for value in values.values():
        if contains_identity(value, target, depth + 1, max_depth, seen):
            return True
    return False

def main():
    result = {
        "release": "O39-S36.3.1",
        "status": "FAIL",
        "service_module": "core.src.service",
        "live_provider_module": "core.src.live_providers",
        "runtime_module": "core.src.real_wiring",
        "checks": {},
        "external_action_executed": False,
        "memory_write_executed": False,
        "notes": [],
    }

    try:
        from core.src import service, live_providers, real_wiring
    except Exception as exc:
        result["notes"].append({
            "stage": "import",
            "error_type": type(exc).__name__,
        })
        OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print("S36_3_1_RUNTIME_PROVIDER_WIRING_FAIL")
        return 1

    try:
        service_source = inspect.getsource(service)
    except OSError:
        service_source = ""

    result["checks"]["service_source_hash"] = safe_hash(service_source)
    result["checks"]["service_imports_live_providers"] = (
        "from .live_providers import model_provider, search_provider" in service_source
    )
    result["checks"]["service_passes_model_provider"] = (
        "model_provider=model_provider" in service_source
    )
    result["checks"]["service_passes_search_provider"] = (
        "search_provider=search_provider" in service_source
    )
    result["checks"]["service_model_provider_identity"] = (
        getattr(service, "model_provider", None) is live_providers.model_provider
    )
    result["checks"]["service_search_provider_identity"] = (
        getattr(service, "search_provider", None) is live_providers.search_provider
    )

    def model_sentinel(prompt):
        return {"provider": "s36_3_1_model_sentinel", "text": "ok"}

    def search_sentinel(query):
        return {"results": [{"title": "s36_3_1_search_sentinel"}]}

    try:
        runtime = real_wiring.O23Runtime(
            model_provider=model_sentinel,
            search_provider=search_sentinel,
        )

        result["checks"]["runtime_model_provider_injected"] = contains_identity(
            runtime, model_sentinel
        )
        result["checks"]["runtime_search_provider_injected"] = contains_identity(
            runtime, search_sentinel
        )
        result["checks"]["runtime_model_provider_callable"] = callable(model_sentinel)
        result["checks"]["runtime_search_provider_callable"] = callable(search_sentinel)

        if not result["checks"]["runtime_model_provider_injected"]:
            result["notes"].append("model_sentinel_not_found_in_runtime_object_graph")
        if not result["checks"]["runtime_search_provider_injected"]:
            result["notes"].append("search_sentinel_not_found_in_runtime_object_graph")
    except Exception as exc:
        result["notes"].append({
            "stage": "runtime_injection",
            "error_type": type(exc).__name__,
        })
        result["checks"]["runtime_model_provider_injected"] = False
        result["checks"]["runtime_search_provider_injected"] = False
        result["checks"]["runtime_model_provider_callable"] = False
        result["checks"]["runtime_search_provider_callable"] = False
    finally:
        try:
            runtime.close()
        except Exception:
            pass

    required = [
        "service_imports_live_providers",
        "service_passes_model_provider",
        "service_passes_search_provider",
        "service_model_provider_identity",
        "service_search_provider_identity",
        "runtime_model_provider_injected",
        "runtime_search_provider_injected",
        "runtime_model_provider_callable",
        "runtime_search_provider_callable",
    ]

    result["status"] = (
        "PASS"
        if all(result["checks"].get(name) is True for name in required)
        and not result["external_action_executed"]
        and not result["memory_write_executed"]
        else "FAIL"
    )

    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        "S36_3_1_RUNTIME_PROVIDER_WIRING_PASS"
        if result["status"] == "PASS"
        else "S36_3_1_RUNTIME_PROVIDER_WIRING_FAIL"
    )
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
