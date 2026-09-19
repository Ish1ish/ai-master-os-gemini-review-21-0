# AI Master OS — O41.4 Decision Surface Integrity

O41.4 hardens the business-facing decision surface so research outputs remain complete, internally consistent, and actionable.

## Fixed
- Canonical `decision_surface` is emitted by the runtime and reused by the Arabic summary and UI.
- Opportunity Score now comes from the ranked opportunity object; Strategy Score is shown separately as a business-model prioritization heuristic.
- Evidence Boundary, total evidence, local-source count, and local-evidence count are exposed together.
- Arabic low-cost constraints are understood deterministically so Service-led validation can outrank premature digital-product build decisions when the constraints demand it.
- Product context now preserves the selected strategy model instead of falling back to `Focused Business Solution`.
- Validation is promoted from a generic question to a measurable experiment with sample size, method, metrics, thresholds, decision rule, timebox, and no-external-action boundary.
- The decision surface explicitly separates `Validation Model` from `Long-term Product Model`.

## Operating loop
`Research → Decision → Validation Experiment → Real-world Evidence → Re-run → Learn → Remember`

## Decision boundary
- Opportunity Score = prioritization heuristic.
- Strategy Score = business-model fit heuristic for the current validation stage.
- Confidence = strength of current evidence, not probability of success.
- Local evidence support still follows the O41 Egypt-first evidence boundary policy.

## Verification
- Backend: 85/85 tests PASS.
- UI Console: 21/21 tests PASS.
- Compileall PASS.
- Existing release evaluation remains RELEASE_CANDIDATE.

## Next phase
The next meaningful step is not external execution. It is to run the user-side Windows gate, then repeat the Arabic Golden Run and verify that the Decision Surface is complete. After that, the next productization target is the real Validation/Evidence Loop before expanding Approval/Control-Plane execution.

- O41.4.2 patch: report export preserves numeric decision scores.
