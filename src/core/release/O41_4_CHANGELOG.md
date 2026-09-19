# O41.4 — Decision Surface Integrity

## Fixed
- Canonical business decision surface added to the runtime output.
- Opportunity Score, Strategy Score, Confidence, and Evidence Boundary now have explicit roles and display paths.
- Local evidence counts are surfaced instead of being reduced to a generic sentence.
- Arabic low-cost constraints influence deterministic strategy model selection.
- Strategy-to-Product context preserves the recommended business model and avoids `Focused Business Solution` fallback when a concrete model exists.
- Validation plan now includes a first executable experiment with sample size, method, measures, success thresholds, decision rule, timebox, and an explicit no-external-action boundary.
- Validation Model and Long-term Product Model are separated in both backend output and UI.

## UI
- UI Console bumped to v1.7.0.
- Business report export includes validation model, long-term product model, success threshold, decision rule, strategy score, and local evidence.
- Arabic result card shows model split, both scores, confidence, validation test, threshold, and evidence boundary.

## Verification
- 85 backend tests PASS.
- 21 UI tests PASS.
- Compileall PASS.
- Existing release evaluation: RELEASE_CANDIDATE.

- O41.4.2: fixed numeric score serialization in the browser-generated Business Report; added regression test.
