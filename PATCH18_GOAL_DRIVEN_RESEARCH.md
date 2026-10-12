# PATCH18 — Goal-Driven Governed Market Research

## Purpose

Add a bounded, read-only, citation-ready market research operation to the canonical S21/O45 runtime. This is an evidence-acquisition building block; it does not claim to be the finished goal-to-business planning system.

## Behavior

- Derives up to six deterministic search queries from the user's goal, audience, and explicitly provided constraints.
- Does not assume a default country or city. Location is added only when supplied.
- Sends only selected context fields (such as location, industry, business model, budget, and timeline) into generated queries; arbitrary fields such as tokens/private notes are not copied into searches.
- Deduplicates results by URL, ignores non-HTTP(S) and credential-bearing URLs, bounds result text/volume, and keeps source title, snippet, domain, matched queries, UTC access time, and published date when supplied by the provider.
- Returns `COMPLETE` or `PARTIAL` when usable cited sources are available. If no citable URLs are collected, it fails through O45 instead of reporting an empty search as success.
- Provider credentials are read only by the existing live-provider client. They are never returned in research results.
- Research is registered as `provider.research.live`; its paired O45 action is `read_only_market_research`, a low-risk, non-external-effect governance action.

## Governed lifecycle

Submitting an execution contract does not call the provider. It creates the intent and O45 receipt. The actual call happens only through the existing explicit execute route after the intent is in a ready state. The research bootstrap may gather evidence before decision-grade market evidence exists, but this narrow exception applies only to the exact action/tool pair above. O45 still independently classifies the operation and writes the execution receipt. No publishing, messaging, spending, integrations, or automatic memory writes are enabled by this patch.

## Example request

Send to `POST /api/runs` using the existing authenticated S21 bearer-token contract:

```json
{
  "run_id": "market-research-001",
  "project_id": "meal-prep-project",
  "strategy_id": "market-research-strategy",
  "intent": "Research demand before recommending a business plan",
  "goal": "Validate demand for affordable home-cooked meals",
  "audience": "busy office workers",
  "requested_language": "en",
  "constraints": {
    "location": "Cairo, Egypt",
    "budget": {
      "amount": 10000,
      "currency": "EGP"
    },
    "business_model": "preorders and local delivery"
  },
  "execution_contract": {
    "action": "read_only_market_research",
    "tool_name": "provider.research.live",
    "payload": {
      "goal": "Validate demand for affordable home-cooked meals",
      "audience": "busy office workers",
      "constraints": {
        "location": "Cairo, Egypt",
        "budget": {
          "amount": 10000,
          "currency": "EGP"
        },
        "business_model": "preorders and local delivery"
      },
      "max_queries": 6
    }
  }
}
```

Use the returned `governed_execution.intent.intent_id` with `POST /api/intents/{intent_id}/execute`. Then inspect `GET /api/executions/{execution_id}`, using the `execution_id` from `governed_execution.submission.execution`. These endpoints retain the current authorization requirements.

## Boundaries and next work

- Requires the existing search-provider environment configuration; no provider, key, model, or search results are bundled.
- Search provider results are leads, not independently verified facts. Downstream analysis should preserve source URLs/dates, distinguish published dates from access times, compare independent sources, and report gaps.
- This patch returns raw bounded evidence. Model-based synthesis, PDF prompt-library ingestion/RAG, an interactive goal intake, project plan generation, and multi-stage project execution remain separate future work.
- `frontend/` is not part of this patch.
