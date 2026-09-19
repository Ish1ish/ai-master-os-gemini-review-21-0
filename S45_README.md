# O45 / S45 — Tool & Action Execution Hardening

Purpose: harden the boundary between a decision/intent and tool/action execution.

Controls:
- capability/least-privilege check
- deterministic consequential-action classification
- explicit approval requirement for external/financial/destructive effects
- self-approval prohibition
- project/requester/capability approval binding
- idempotency receipts
- execution receipts
- fail-closed behavior
- consequential external execution disabled by default

This release does not enable autonomous consequential actions.
