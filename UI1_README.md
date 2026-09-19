# O46 UI-1 — Unified Experience Data Contract + Experience Shell

Purpose: create the first product-facing experience layer over the O46 runtime without adding side effects.

## Included
- Canonical `o46_experience_view.schema.json` with run → intent → research → decision → governance → approval → execution → outcome → learning → next_step → provenance.
- Executive experience shell on the existing overview page.
- Read-only aggregation from `/runs`, `/runs/{job_id}`, `/learning/context`, `/experiments`, and `/approvals` when exposed.
- Journey rail, decision surface, evidence summary, governance state, outcome/learning summary, and explainability trace.
- Graceful unavailable states; no invented live data.
- No execute/send/publish actions added by this layer.

## Validation
`src/ui/tests/test_o46_experience_shell.py`

Gate:
`scripts/ui1_o46_experience_shell_gate.py`
