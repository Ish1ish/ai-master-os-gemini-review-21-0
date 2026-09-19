# O39-S42 — Security & Failure Chaos Drill

Combined dependency-free chaos validation for the O39 resilience layers already built.

Scenarios:
- transient model/provider 5xx with bounded recovery
- 429 rate-limit recovery
- bounded concurrent runtime load
- contained runtime failure
- worker interruption + restart reconciliation
- terminal recovery after requeue
- duplicate lease protection
- provider snapshot safety

No network calls, secrets, persistent production state, external consequential actions,
or automatic memory writes are performed by this release gate.

User verification must be performed from the existing unified workspace. The gate also
checks that the existing ApplicationService lifecycle is present before declaring PASS.
