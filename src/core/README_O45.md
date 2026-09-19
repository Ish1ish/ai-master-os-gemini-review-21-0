
# O45 Build — Tool / Action Execution Hardening

This directory is the O44 frozen baseline plus the O45 execution-hardening layer.

O45 adds:
- explicit ToolRegistry
- canonical request hashing
- durable idempotency keys
- execution receipts and state machine
- single-owner execution leases
- exact approval binding to project/run/action
- fail-closed unknown tool/action behavior
- terminal replay protection
- retryable vs terminal error classification
- recovery-required state after expired execution leases
- Windows verification wrapper
