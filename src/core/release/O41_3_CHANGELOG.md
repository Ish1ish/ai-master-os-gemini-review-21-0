# O41.3 — Decision Quality + Arabic Understanding Hardening

## Fixed
- Stronger Egypt-first research planning with segment/problem/competitor scans instead of repeating the full user request.
- More conservative geographic evidence classification so a global article mentioning Egypt once is not treated as local evidence.
- Local evidence boundary now requires multiple local sources/evidence items before being marked locally supported.
- Product identity, positioning handoff, content topics, offer naming, and sales naming remain enforced from O41.3.
- Arabic decision summary remains the primary human-readable decision surface when `language=ar`.

## User-facing operating loop
`Research → Recommendation → One validation test → Real-world evidence → Re-run`

## Boundary
Scores remain prioritization heuristics. Global signals still require local validation when local evidence is insufficient.
