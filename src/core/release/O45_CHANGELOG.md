# O45 Changelog

## O45-v1.0.0 — Tool / Action Execution Hardening

Built on the O44 verified baseline.

Added:
- explicit ToolRegistry with disabled/unknown-tool fail-closed behavior
- canonical execution request hashing
- durable idempotency keys
- durable execution receipts and state machine
- atomic single-owner execution leases
- human approval binding to exact project/run/action/request hash
- terminal replay protection
- durable execution-event audit trail
- explicit retry-safe tool declaration
- `RECOVERY_REQUIRED` for ambiguous external outcomes
- O45 smoke and Windows verification scripts
- O45 execution schema and runbook documentation

Verification performed in the development environment:
- 143/143 backend tests PASS
- compileall PASS
- O44 governance smoke PASS
- O45 execution smoke PASS

User-side Windows verification is intentionally still pending.
