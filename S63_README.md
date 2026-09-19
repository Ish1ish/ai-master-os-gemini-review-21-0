# O46-S63 — Approval Persistence + Resume

Adds a durable, atomic JSON checkpoint for the human approval boundary. The checkpoint stores only approval workflow state and trace identifiers; it is not business memory.

Guarantees:
- `AWAITING_APPROVAL` survives process restart.
- The same `action_id`, request fingerprint, and cycle trace IDs are resumed.
- Resume does not re-run the provider loop when a pending checkpoint exists.
- Explicit approval/rejection updates the checkpoint idempotently.
- Approval releases only to the downstream execution layer; this module never executes an external action.
- No automatic memory write is performed.

Targeted suite: `S63_TARGETED_TESTS_PASS 18/18`.
