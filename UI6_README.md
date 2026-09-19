# UI-6 — O46 Governance & Approval Center

Purpose: turn the existing backend-authoritative approval surface into an understandable, premium governance experience without adding autonomy.

Adds:
- governance experience hero
- clear awaiting-human-decision state
- risk / external impact / impact / policy / idempotency binding summary
- richer approval inspector
- optional raw payload details
- RTL + responsive presentation

Safety:
- approval actions remain backend-bound
- UI is not policy authority
- no local auto-approval
- no new execution controls

Gate: `scripts/ui6_o46_governance_center_gate.py`
