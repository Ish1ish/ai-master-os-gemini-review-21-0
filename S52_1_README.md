O45-S52.1 — Real Provider Closed Loop Gate Wiring Fix

Fixes a gate false-negative where trace_snapshot() was assumed to be keyed directly by trace_id. The gate now resolves traces by key or by the trace object's trace_id, matching the existing test contract. No provider logic, execution policy, memory behavior, or external-action behavior is changed.
