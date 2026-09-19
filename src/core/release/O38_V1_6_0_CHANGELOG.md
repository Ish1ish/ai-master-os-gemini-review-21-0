# O38 v1.6.0 — Runtime + Semantic Hardening

## Runtime fixes
- Persist audience/goal/constraints with each submitted run, including migration for existing `jobs` databases.
- Atomically claim `QUEUED -> RUNNING` jobs to prevent duplicate execution across concurrent API/worker calls.
- Add `run:execute` and `run:list` policy scopes and enforce execute authorization at the service boundary.
- Persist richer runtime failure diagnostics instead of reducing failures to a stage/status pair.
- Expose authenticated `GET /runs` for server-backed run history.
- Start monitoring from the service execution boundary and close failed runs when runtime execution fails.

## Semantic fixes
- Stronger raw-evidence detection and Quick Answer/URL contamination guards.
- Strategy-to-product now prefers canonical evidence summaries over free-form positioning as the product problem source.
- Product definitions canonicalize problem/audience/positioning fields.

## Compatibility
- Existing O38 SQLite job databases are migrated in place via `context_json`.
- Worker execution uses an explicit internal path so queue workers are not treated as external API callers.
