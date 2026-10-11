# PATCH20 — One-goal research workflow

## Purpose

PATCH20 adds a composite O45 tool named `provider.research.workflow`. The caller supplies a business goal, audience, optional location/budget/other allowlisted constraints, and a requested report language. One explicit governed execution then runs the existing bounded PATCH18 search stage and passes its validated, citation-ready results to the PATCH19 synthesis stage.

This is an orchestration step, not a new search engine and not an autonomous business-execution capability.

## Governed lifecycle

1. Submit an intent with action `read_only_market_research` and tool `provider.research.workflow`.
2. The submit call creates and evaluates a governed intent without calling the search or model provider.
3. Explicitly execute the intent through the canonical O45 drive path.
4. The composite tool performs at most six goal-aware search queries, validates source URLs, then calls the configured model once to generate a structured synthesis.
5. The result preserves the search status, per-query statuses, query count, source ID/URL map, matched query provenance, and structured synthesis.

S21 registers the composite with `retry_safe=False`. The governance bootstrap allowlist accepts only the three explicit research tools `provider.research.live`, `provider.research.synthesis`, and `provider.research.workflow` under the `read_only_market_research` action. Other tool names remain blocked.

## Output outline

- `workflow_stages`: research and synthesis statuses, query/result counts
- `research`: bounded queries and per-query status, including partial failures
- `sources`: source IDs, URLs, titles, domains, access/publication dates when available, and matched query provenance
- `synthesis`: executive summary, source-backed observations, hypotheses, recommendations, risks, and evidence gaps
- `evidence_boundary`: marks that this is a synthesis of search-result snippets, not verification of complete source pages
- `decision_grade_evidence: false`

A partial search remains marked as `PARTIAL` even when synthesis succeeds. If synthesis fails validation or the model provider fails, the composite does not return a misleading completed report; the error is recorded through the governed execution path.

## Example payload

```json
{
  "action": "read_only_market_research",
  "tool_name": "provider.research.workflow",
  "payload": {
    "goal": "Validate demand for affordable home-cooked meals",
    "audience": "busy office workers",
    "constraints": {
      "location": "Cairo, Egypt",
      "budget": { "amount": 10000, "currency": "EGP" },
      "timeline": "30 days"
    },
    "requested_language": "ar",
    "max_queries": 6
  }
}
```

Submit-only versus execution is unchanged: the example above is an intent payload, and the caller must explicitly drive the returned intent through the governed execute route.

## Validation

`tests/test_patch20_goal_research_workflow.py` covers order and payload handoff, partial-state preservation, validation errors, source query provenance, and submit-only/governed-drive execution. `tests/test_s21_http_composition.py` checks registration and `retry_safe=False`.

Focused and full regression tests must be run in the project's local Python environment before merge. No live-provider execution is claimed by mocked unit tests.
