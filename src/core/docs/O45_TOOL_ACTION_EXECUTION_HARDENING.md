# O45 — Tool / Action Execution Hardening

## Purpose

O45 turns the O44 governance decision into a **safe execution boundary**.

The rule is:

`Request → Canonicalize → O44 Governance → Approval (when required) → READY → Lease/Claim → Tool Execution → Receipt → Audit/Recovery`

O45 does **not** replace O44. O44 remains authoritative for whether an action is `AUTO_ALLOW`, `REVIEW`, or `BLOCK`.

## Security and reliability guarantees

- Unknown tools fail closed.
- Unknown O44 actions fail closed.
- `BLOCK` never reaches a tool handler.
- `REVIEW` never reaches a tool handler until the exact approval is `APPROVED`.
- Approval is bound to project, run, action, and approval id.
- Idempotency keys are durable and cannot be reused with a different request.
- Two workers cannot claim the same `READY` execution.
- Tool handlers receive only the canonical payload.
- Tool disablement is checked immediately before execution.
- Terminal results are replay-safe: a second call returns the existing receipt instead of executing again.
- Expired execution leases become `RECOVERY_REQUIRED`; O45 does not automatically retry an operation whose external outcome may be unknown.
- Errors are persisted as bounded, structured data.
- Receipt state and execution metadata survive process restart in SQLite.
- State transitions are recorded in a durable execution-event audit trail.
- A failed tool is retryable only when its registry entry explicitly declares `retry_safe`; otherwise O45 enters `RECOVERY_REQUIRED`.

## State model

`AWAITING_APPROVAL → READY → RUNNING → SUCCEEDED`

Failure branches:

`RUNNING → FAILED_RETRYABLE`

or:

`RUNNING → FAILED_TERMINAL`

Crash/lease ambiguity:

`RUNNING → RECOVERY_REQUIRED`

Other terminal controls:

`READY/AWAITING_APPROVAL → CANCELLED`

Governance block:

`BLOCKED`

## Human governance

For consequential actions, O44 creates an approval request. O45 only becomes executable after the approval record is `APPROVED` and matches the execution request.

An approval is not execution. It is a prerequisite to enter the execution state.

## Idempotency

Clients must supply an `idempotency_key`.

The same key with the same canonical request returns the existing execution receipt.

The same key with a different request is a deterministic `CONFLICT`.

## Recovery rule

A worker lease is a processing ownership mechanism, not proof that an external side effect did or did not happen.

Therefore an expired lease is marked `RECOVERY_REQUIRED` rather than silently retried. Reconciliation must happen before a new side-effecting attempt is allowed.

## O45 boundary

O45 is the execution-hardening layer. Real external tools/connectors are intentionally registered explicitly through `ToolRegistry`.

No external publication, messaging, spending, deletion, or integration activation is enabled merely by installing O45.
