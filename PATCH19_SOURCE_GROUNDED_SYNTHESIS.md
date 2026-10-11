# PATCH19 — Source-grounded research synthesis

## Purpose

PATCH19 adds a second read-only provider tool to the canonical S21/O45 surface. PATCH18 collects goal-driven search results with source URLs and provenance; PATCH19 synthesizes a supplied results list into a structured market-research brief.

The synthesis tool does not issue search requests. The caller must pass the `results` list from a prior `provider.research.live` execution. This keeps evidence acquisition and model interpretation separate and inspectable.

## Governed lifecycle

1. Submit an intent using action `read_only_market_research` and tool `provider.research.live`.
2. Explicitly drive the returned intent. The result includes URL-validated source records and query provenance.
3. Submit a second intent using the same read-only action and the exact tool `provider.research.synthesis`, passing the goal, audience, requested language, and prior results list.
4. Explicitly drive the synthesis intent. Submission itself does not invoke the model.

The research action can bind only to `provider.research.live` or `provider.research.synthesis`. Any other tool name is blocked. Both tools are registered with `retry_safe=False`.

## Output contract

The synthesis result includes:

- `executive_summary`
- `evidence_findings`: claims required to cite one or more known `source_id` values
- `hypotheses`: possible explanations that remain hypotheses and include a validation step
- `recommendations`: actions with assumptions and a validation step
- `risks`
- `evidence_gaps`
- `sources`: a source-ID-to-URL map for rendering citations

Unknown source IDs, missing citations on evidence findings, invalid JSON, and malformed required fields fail closed. Snippets and titles are bounded, source URLs are normalized, and only a small allowlisted record shape is sent to the model. Source text is explicitly treated as untrusted data rather than instructions.

## Evidence boundary

The tool marks its result with:

`evidence_boundary = SYNTHESIS_OF_SUPPLIED_SEARCH_SNIPPETS_NOT_FULL_PAGE_VERIFICATION`

and `decision_grade_evidence = false`. Citation-ID validation prevents the model from inventing a new source reference, but it cannot prove semantic entailment between a claim and a source snippet. Human/source-page validation is still needed before a consequential business decision. The model output does not silently become decision-grade evidence.

## Example execution payload

For the second governed intent:

```json
{
  "action": "read_only_market_research",
  "tool_name": "provider.research.synthesis",
  "payload": {
    "goal": "Validate demand for affordable home-cooked meals",
    "audience": "busy office workers",
    "requested_language": "ar",
    "results": [
      {
        "url": "https://example.com/market-report",
        "title": "Example market report",
        "snippet": "A bounded search-result excerpt.",
        "published_at": "2026-09-18",
        "accessed_at": "2026-10-11T10:00:00Z"
      }
    ]
  }
}
```

This is an example payload only; its sample URL and claim are not market evidence.

## Tests

`tests/test_patch19_source_grounded_synthesis.py` covers structured output, source mapping, unknown or missing citations, malformed output, safe provider failures, empty sources, and the submit-only/governed-drive lifecycle. `tests/test_s21_http_composition.py` verifies the synthesis tool is registered and is not marked retry-safe.

Tests must be run in the project's local Python environment before the patch is considered ready. No live model call is claimed by the deterministic unit tests.
