# PATCH21 — Research-grounded project plan draft

## Purpose

PATCH21 adds an internal-only draft generator named `provider.project.plan`. It consumes the user's goal, an allowlisted subset of the user's constraints, and the structured output from the PATCH20 `provider.research.workflow` stage.

It generates a practical plan draft containing:
- Project title, executive summary, recommended approach, and minimum viable launch
- Assumptions and methods to test them
- Ordered milestones with day ranges, tasks, and completion criteria
- Budget line items with explicit basis labels
- Success metrics, risks, immediate next actions, and open questions

## Budget honesty contract

Each budget item must use one of three bases:
- `source_supported`: numeric range plus at least one known source ID, and only when the supplied evidence directly supports the cost and a known currency is available
- `planning_estimate`: numeric low/high range, a known currency, explanatory notes, and at least one explicit assumption; these are not quotes
- `unknown`: both amount fields must be null

Currency is taken from the user's supplied budget metadata or a recognizable currency code in their budget string. If it cannot be determined, the tool rejects numeric cost estimates and requires unknown costs instead. It never silently invents a currency. It preserves the user's budget text separately from itemized estimates.

A known source ID is not proof that a source semantically entails a cost claim. The model prompt instructs conservative use; human/source-page review remains necessary.

## Research and source boundary

The input `research` must be the object produced by the prior research workflow and include a source map plus synthesis. The tool validates source IDs against the supplied URL-normalized source list, checks all citation IDs, and passes a bounded safe subset of the user's constraints. Other arbitrary constraint fields, including token-shaped fields, are not forwarded to the model.

The output is labeled `plan_type=INTERNAL_DRAFT`, `decision_grade_evidence=false`, and `external_actions_executed=false`. The plan does not place orders, contact customers, publish content, spend money, or create scheduled workflows.

## Governed lifecycle

Use action `generate_internal_draft` with the exact tool `provider.project.plan`. Submission creates a governed intent only. The model provider runs only after the caller explicitly executes the intent through the O45 drive path.

S21 registers the tool as `retry_safe=False`. The runtime bootstrap exception applies only to this exact action/tool pair and supplies evidence that describes the user's request scope, not confidence in market claims.

## Example governed intent payload

```json
{
  "action": "generate_internal_draft",
  "tool_name": "provider.project.plan",
  "payload": {
    "goal": "Validate demand for affordable home-cooked meals",
    "audience": "busy office workers",
    "constraints": {
      "location": "Cairo, Egypt",
      "budget": { "amount": 10000, "currency": "EGP" },
      "timeline": "30 days"
    },
    "requested_language": "ar",
    "research": {
      "status": "COMPLETE",
      "goal": "Validate demand",
      "audience": "office workers",
      "sources": [
        {
          "source_id": "S001",
          "url": "https://example.com/market-report",
          "title": "Illustrative source title",
          "domain": "example.com"
        }
      ],
      "synthesis": {
        "executive_summary": "Illustrative summary",
        "evidence_findings": [
          { "claim": "Illustrative evidence claim", "source_ids": ["S001"], "confidence": "low" }
        ],
        "hypotheses": [],
        "recommendations": [],
        "risks": [],
        "evidence_gaps": ["Full page review is still required."]
      }
    }
  }
}
```

The example is a contract shape only; its URL and claims are not real market evidence.

## Validation

`tests/test_patch21_project_plan_generator.py` exercises the structured schema, source IDs, currency requirements, budget-range checks, source prompt-injection handling, safe provider failures, and explicit governed execution. `tests/test_s21_http_composition.py` asserts S21 registration and `retry_safe=False`.

Run the targeted tests in the local project environment before merging. Per the project workflow, the long full-regression suite is not required for each incremental patch. No live provider run is claimed by these deterministic unit tests.
