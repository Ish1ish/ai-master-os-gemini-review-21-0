# Phase 2 Execution Planning v1.2.0

The planner is intentionally not an executor. It consumes a Unified Decision Intelligence plan and emits a deterministic Execution Intent only when the decision status is `RECOMMEND`.

The produced intent contains:
- deterministic intent ID
- deterministic idempotency key
- selected provider/tool route
- explicit action and payload
- project/run/requester identity
- decision basis
- governance-review requirement
- execution-request envelope compatible with the O45 request boundary
- explicit execution/recovery flags

The planner performs preflight integrity checks but delegates authorization and actual execution to the existing governance/execution stack.
