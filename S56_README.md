# O45-S56 — Cost-Aware Adaptive Recovery

Adds a deterministic hard budget around the S55 adaptive recovery policy.
The layer limits estimated provider calls and recovery units, preserves traceable evidence,
and fail-closes when even one bounded recovery attempt cannot fit the configured budget.

No provider call, external action, approval, or AI-memory write is executed by this layer.

Verification:
- Native targeted tests: 15/15
- compileall
- within-budget recovery
- budget-exceeded fail-closed
- deterministic budget ID
- idempotent repository
