import json
import os
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

from .provider_resilience import ProviderRequestError, call_with_provider_reliability


def _http_json_once(url, api_key, payload, timeout):
    body = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        retry_after = None
        try:
            retry_after = float(exc.headers.get("Retry-After")) if exc.headers.get("Retry-After") else None
        except (TypeError, ValueError):
            retry_after = None
        raise ProviderRequestError(
            f"provider_http_error:{exc.code}:{exc.reason}",
            status_code=int(exc.code),
            retry_after=retry_after,
        ) from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ProviderRequestError(f"provider_request_failed:{type(exc).__name__}:{exc}") from exc


def _http_json(url, api_key, payload, timeout):
    provider = "model" if payload.get("messages") is not None else "search"
    return call_with_provider_reliability(
        provider,
        lambda: _http_json_once(url, api_key, payload, timeout),
    )


def model_provider(prompt):
    url = os.getenv("AI_OS_MODEL_BASE_URL")
    key = os.getenv("AI_OS_MODEL_API_KEY")
    model = os.getenv("AI_OS_MODEL_NAME")
    timeout = float(os.getenv("AI_OS_REQUEST_TIMEOUT_S", "30"))
    if not url or not key or not model:
        raise RuntimeError("model provider configuration is incomplete")
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "reasoning_effort": os.getenv("AI_OS_MODEL_REASONING_EFFORT", "low")}
    result = _http_json(url, key, payload, timeout)
    text = ""
    choices = result.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {})
        text = message.get("content", "") if isinstance(message, dict) else ""
    text = text or result.get("output_text") or result.get("text") or ""
    if not text:
        raise RuntimeError("model provider response missing text")
    return {"provider": url, "model": model, "text": text}


def search_provider(query):
    url = os.getenv("AI_OS_SEARCH_BASE_URL")
    key = os.getenv("AI_OS_SEARCH_API_KEY")
    timeout = float(os.getenv("AI_OS_REQUEST_TIMEOUT_S", "30"))
    if not url or not key:
        raise RuntimeError("search provider configuration is incomplete")
    result = _http_json(url, key, {"query": query}, timeout)
    rows = result.get("results", [])
    if not isinstance(rows, list):
        raise RuntimeError("search provider response missing results list")
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        item = dict(row)
        if not item.get("snippet") and item.get("content"):
            item["snippet"] = item.get("content")
        normalized.append(item)
    if not normalized:
        raise RuntimeError("search provider returned no usable results")
    return {"results": normalized}


def provider_configuration_status():
    required = [
        "AI_OS_MODEL_BASE_URL",
        "AI_OS_MODEL_API_KEY",
        "AI_OS_MODEL_NAME",
        "AI_OS_SEARCH_BASE_URL",
        "AI_OS_SEARCH_API_KEY",
    ]
    missing = [name for name in required if not os.getenv(name)]
    return {"status": "CONFIGURED" if not missing else "NOT_CONFIGURED", "missing": missing}
