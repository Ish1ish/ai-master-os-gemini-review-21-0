# AI Master OS — O44 Governance Intelligence v1.0.0

O44 adds deterministic risk classification and approval intelligence. It does not perform consequential external actions by itself.

Operating loop:
`Classify → Risk → AUTO_ALLOW / REVIEW / BLOCK → Human Approval when required → Audit
`

Key rules:
- Unknown actions fail closed.
- External, financial, destructive, or otherwise consequential actions require review.
- AUTO_ALLOW is reserved for bounded internal actions with sufficient evidence and confidence.
- Approval self-review is rejected.
- Approval decisions persist in SQLite.

API:
- `POST /governance/evaluate`
- `GET /governance/decisions`
- `GET /governance/decisions/{decision_id}`
- `GET /approvals/pending`
- `GET /approvals/{approval_id}`
- `POST /approvals/{approval_id}/decision`

---

# O46 GOVERNED AUTONOMOUS LOOP

O46 adds the bounded end-to-end cycle above the O44 governance and O45 execution layers. See `README_O46.md`.

## v0.8 Bounded Self-Optimization

`src/bounded_self_optimization.py` provides the deterministic Observe → Propose → Simulate → Evaluate → Govern → Apply/Rollback boundary. `src/optimization_store.py` provides auditable durable state. Simulation does not change production state; governance remains authoritative.


## Phase 2 / v1.1.0 Unified Decision Intelligence

Added `src/unified_decision_intelligence.py` for deterministic, advisory-only route planning that combines uncertainty, reliability, production pressure, and candidate evidence.
