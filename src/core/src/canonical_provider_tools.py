"""Canonical O45 tool adapters over the real live provider clients.

These wrappers translate the O45 ExecutionService's payload-dict handler
contract into read-only live-provider calls. Credentials stay inside
live_providers and are never logged or returned.

Only advisory/read-only provider operations are exposed here. The governed O45
execution path remains responsible for authorization, approvals, receipts, and
failure classification.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Mapping
from urllib.parse import urlsplit, urlunsplit

from .live_providers import search_provider


MAX_RESEARCH_QUERIES = 6
MAX_RESEARCH_RESULTS = 30
MAX_TITLE_CHARS = 240
MAX_SNIPPET_CHARS = 2000


def real_search_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
    """O45 tool handler: one real, read-only search-provider call.

    Payload contract: {"query": <non-empty string>}. Provider failures are
    intentionally allowed to reach O45 so the governed executor classifies
    them and persists the outcome.
    """
    query = str((payload or {}).get("query") or "").strip()
    if not query:
        raise ValueError("query_required")
    result = search_provider(query)
    rows = result.get("results", [])
    return {
        "provider": "live_search",
        "query": query,
        "result_count": len(rows),
        "results": rows,
    }


def _clean_text(value: Any, *, limit: int = 180) -> str:
    """Normalize bounded text without serializing arbitrary Python objects."""
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, (str, int, float)):
        return " ".join(str(value).split())[:limit]
    if isinstance(value, (list, tuple)):
        pieces = [_clean_text(item, limit=limit) for item in value]
        return " ".join(piece for piece in pieces if piece)[:limit]
    if isinstance(value, Mapping):
        pieces = []
        for key in sorted(value, key=lambda item: str(item)):
            piece = _clean_text(value[key], limit=limit)
            if piece:
                pieces.append(piece)
        return " ".join(pieces)[:limit]
    return ""


def _constraint_text(constraints: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = constraints.get(key)
        rendered = _clean_text(value, limit=180)
        if rendered:
            return rendered
    return ""


def _budget_text(value: Any) -> str:
    if isinstance(value, Mapping):
        amount = _clean_text(value.get("amount", value.get("value")), limit=80)
        currency = _clean_text(value.get("currency"), limit=30)
        if amount and currency:
            return f"{amount} {currency}"
    return _clean_text(value, limit=100)


def build_research_queries(
    goal: str,
    audience: str = "",
    constraints: Mapping[str, Any] | None = None,
) -> list[str]:
    """Build stable, bounded, goal-aware market research queries.

    Geography is included only when supplied by the caller; this deliberately
    avoids assuming Egypt (or any other location) for every project. Only
    selected constraint fields are used so unrelated/private input fields do
    not leak into provider queries.
    """
    goal_text = _clean_text(goal, limit=500)
    if not goal_text:
        raise ValueError("goal_required")
    if constraints is not None and not isinstance(constraints, Mapping):
        raise ValueError("constraints_must_be_mapping")

    details = dict(constraints or {})
    audience_text = _clean_text(audience, limit=240)
    location = _constraint_text(
        details, "location", "target_location", "city", "region", "country",
        "geography", "target_geography",
    )
    industry = _constraint_text(details, "industry", "sector", "category")
    model = _constraint_text(details, "business_model", "delivery_model", "channel_mode")
    budget = _budget_text(details.get("budget"))
    if not budget:
        budget = _budget_text(details.get("available_budget"))
    timeline = _constraint_text(details, "timeline", "time_horizon")

    subject = " ".join(part for part in (goal_text, industry, model) if part)
    geography = f" in {location}" if location else ""
    target = f" targeting {audience_text}" if audience_text else ""
    budget_hint = f" with a budget of {budget}" if budget else ""
    time_hint = f" within {timeline}" if timeline else ""

    queries = [
        f"{subject}{geography} market demand and customer pain points{target}",
        f"{subject}{geography} competitors, alternatives, and market pricing",
        f"startup costs, operating costs, and unit economics for {subject}{geography}{budget_hint}",
        f"customer acquisition channels for {subject}{target}{geography}",
        f"low-cost ways to validate demand for {subject}{target}{geography}{budget_hint}{time_hint}",
        (
            f"legal requirements, permits, and regulations for {subject}{geography}"
            if location
            else f"common risks, failure modes, and validation pitfalls for {subject}{target}"
        ),
    ]
    # De-duplicate without changing order. Keep all queries bounded for APIs/logs.
    bounded = []
    seen = set()
    for query in queries:
        query = " ".join(query.split())[:700]
        key = query.casefold()
        if query and key not in seen:
            seen.add(key)
            bounded.append(query)
    return bounded[:MAX_RESEARCH_QUERIES]


def _source_url(row: Mapping[str, Any]) -> str:
    raw_url = _clean_text(
        row.get("url") or row.get("link") or row.get("source_url"),
        limit=1800,
    )
    if not raw_url:
        return ""
    try:
        parsed = urlsplit(raw_url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return ""
        if parsed.username or parsed.password:
            return ""
        # Fragments are client-side navigation and are not part of source identity.
        return urlunsplit((parsed.scheme.lower(), parsed.netloc, parsed.path, parsed.query, ""))
    except (TypeError, ValueError):
        return ""


def real_research_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run bounded, read-only research and return citation-ready source records.

    Payload contract:
      {"goal": str, "audience": str?, "constraints": mapping?,
       "max_queries": int?}

    At most six search queries are issued to the provider client; its configured\n    reliability layer may retry underlying HTTP requests. Each source includes its URL,
    title, snippet, query provenance, and UTC access timestamp. Individual query
    failures are reported as partial research when other valid sources exist;
    if no citable source is collected, an exception reaches O45 and the entire
    tool call is classified by the governed execution service.
    """
    if not isinstance(payload, Mapping):
        raise TypeError("research_payload_must_be_mapping")

    queries = build_research_queries(
        str(payload.get("goal") or ""),
        str(payload.get("audience") or ""),
        payload.get("constraints") or {},
    )
    raw_limit = payload.get("max_queries", MAX_RESEARCH_QUERIES)
    try:
        max_queries = int(raw_limit)
    except (TypeError, ValueError) as exc:
        raise ValueError("max_queries_invalid") from exc
    if isinstance(raw_limit, bool):
        raise ValueError("max_queries_invalid")
    max_queries = max(1, min(max_queries, MAX_RESEARCH_QUERIES))
    queries = queries[:max_queries]

    accessed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    sources: list[dict[str, Any]] = []
    source_by_url: dict[str, dict[str, Any]] = {}
    query_statuses: list[dict[str, Any]] = []

    for query in queries:
        try:
            response = search_provider(query)
            rows = response.get("results", []) if isinstance(response, Mapping) else []
            if not isinstance(rows, list):
                rows = []
        except Exception as exc:
            query_statuses.append({
                "query": query,
                "status": "FAILED",
                "error_type": type(exc).__name__,
                "reason": "provider_query_failed",
                "source_count": 0,
            })
            continue

        valid_count = 0
        for row in rows[:MAX_RESEARCH_RESULTS]:
            if not isinstance(row, Mapping):
                continue
            url = _source_url(row)
            if not url:
                continue
            valid_count += 1
            dedupe_key = url.casefold()
            existing = source_by_url.get(dedupe_key)
            if existing is not None:
                if query not in existing["matched_queries"]:
                    existing["matched_queries"].append(query)
                continue
            if len(sources) >= MAX_RESEARCH_RESULTS:
                break

            parsed = urlsplit(url)
            hostname = (parsed.hostname or "").lower()
            if hostname.startswith("www."):
                hostname = hostname[4:]
            title = _clean_text(row.get("title"), limit=MAX_TITLE_CHARS) or hostname
            snippet = _clean_text(
                row.get("snippet") or row.get("content") or row.get("description"),
                limit=MAX_SNIPPET_CHARS,
            )
            source = {
                "url": url,
                "title": title,
                "snippet": snippet,
                "source": hostname,
                "query": query,
                "matched_queries": [query],
                "accessed_at": accessed_at,
            }
            published_at = _clean_text(
                row.get("published_at") or row.get("published_date") or row.get("date"),
                limit=100,
            )
            if published_at:
                source["published_at"] = published_at
            sources.append(source)
            source_by_url[dedupe_key] = source

        query_statuses.append({
            "query": query,
            "status": "SUCCEEDED" if valid_count else "NO_CITABLE_SOURCES",
            "source_count": valid_count,
        })

    if not sources:
        if any(item["status"] == "FAILED" for item in query_statuses):
            raise RuntimeError("research_provider_failed")
        raise RuntimeError("research_results_missing_citable_urls")

    partial = any(item["status"] != "SUCCEEDED" for item in query_statuses)
    return {
        "provider": "live_search",
        "status": "PARTIAL" if partial else "COMPLETE",
        "goal": _clean_text(payload.get("goal"), limit=500),
        "audience": _clean_text(payload.get("audience"), limit=240),
        "queries": queries,
        "query_count": len(queries),
        "query_statuses": query_statuses,
        "result_count": len(sources),
        "results": sources,
    }
