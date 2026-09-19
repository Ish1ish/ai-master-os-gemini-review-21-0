from __future__ import annotations

import json
import os
import time
from pathlib import Path

from core.src.config import RuntimeConfig
from core.src.host import ProductionHost

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "staging" / "provider_evidence"
OUT.mkdir(parents=True, exist_ok=True)

SENSITIVE = {
    "AI_OS_MODEL_API_KEY",
    "AI_OS_SEARCH_API_KEY",
    "AI_OS_IDENTITY_SIGNING_SECRET",
    "AUTHORIZATION",
    "TOKEN",
    "PASSWORD",
}

def safe_error(exc: BaseException) -> dict:
    return {"type": type(exc).__name__}

def main() -> int:
    cfg = RuntimeConfig.from_env()
    readiness = {
        "model": cfg.validate(require_model=True),
        "search": cfg.validate(require_search=True),
        "request_timeout_s": cfg.request_timeout_s,
        "model_configured": bool(cfg.model_base_url and cfg.model_api_key and cfg.model_name),
        "search_configured": bool(cfg.search_base_url and cfg.search_api_key),
    }

    result = {
        "release": "O39-S36",
        "staging": True,
        "provider_readiness": readiness,
        "model": {"status": "NOT_RUN"},
        "search": {"status": "NOT_RUN"},
        "secret_safe": True,
    }

    if readiness["model"]["status"] != "PASS" or readiness["search"]["status"] != "PASS":
        result["status"] = "FAIL_CONFIG"
        OUT.joinpath("s36_provider_evidence.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        print("S36_REAL_PROVIDER_STAGING_FAIL_CONFIG")
        return 1

    host = None
    try:
        host = ProductionHost(config=cfg)

        started = time.perf_counter()
        model = host.build_model_provider()
        model_out = model.generate(
            "Return exactly the JSON object {\"staging_probe\":\"ok\"} and no other text."
        )
        model_ms = int((time.perf_counter() - started) * 1000)

        result["model"] = {
            "status": model_out.get("status"),
            "provider": model_out.get("provider"),
            "model": model_out.get("model"),
            "latency_ms": model_ms,
        }

        started = time.perf_counter()
        search = host.build_search_provider()
        search_out = search.search("AI operating system staging provider verification")
        search_ms = int((time.perf_counter() - started) * 1000)

        results = search_out.get("results") if isinstance(search_out, dict) else None
        result["search"] = {
            "status": search_out.get("status") if isinstance(search_out, dict) else "INVALID",
            "result_count": len(results) if isinstance(results, list) else 0,
            "latency_ms": search_ms,
        }

        model_ok = result["model"]["status"] == "EXECUTED"
        search_ok = result["search"]["status"] == "SUCCESS" and result["search"]["result_count"] > 0
        result["status"] = "PASS" if model_ok and search_ok else "FAIL_PROVIDER_BEHAVIOR"

    except Exception as exc:
        result["status"] = "FAIL_PROVIDER_EXCEPTION"
        result["exception"] = safe_error(exc)
    finally:
        if host is not None:
            try:
                host.close()
            except Exception:
                pass

    OUT.joinpath("s36_provider_evidence.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print("S36_REAL_PROVIDER_STAGING_" + result["status"])
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
