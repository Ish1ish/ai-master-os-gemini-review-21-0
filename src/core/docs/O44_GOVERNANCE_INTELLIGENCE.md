# O44 — Governance Intelligence

## Goal
Turn the existing approval boundary into a deterministic governance decision layer without granting autonomous external authority.

## Policy
`Classify → Risk → AUTO_ALLOW / REVIEW / BLOCK → Human Approval → Audit`

### AUTO_ALLOW
Reserved for bounded internal actions where risk is low, evidence is provenance-bound, and confidence is high.

### REVIEW
Used for high-risk, consequential, sensitive, or insufficiently evidenced actions. A persistent approval request is created when requested by the API caller.

### BLOCK
Unknown actions and malformed/unsupported governance cases fail closed.

## Consequential action rule
External effects, financial actions, destructive actions, and critical-data mutations cannot be auto-allowed.

## Approval authority
Approval requires an `approver` or `admin` role. Self-approval is rejected.

## Persistence
Governance decisions and approval records persist in SQLite for traceability and restart safety.

## API
- `POST /governance/evaluate`
- `GET /governance/decisions`
- `GET /governance/decisions/{decision_id}`
- `GET /approvals/pending`
- `GET /approvals/{approval_id}`
- `POST /approvals/{approval_id}/decision`
