# AI Master OS — Thin Node BFF

This directory is the Phase 22 transport boundary for the canonical Python S21 API.

## Authority rule

Node is transport only. Python S21 remains authoritative for:

- security admission and identity
- governance
- approvals
- O45 execution
- O46 governed orchestration
- persistence and replay
- tools/providers

The BFF does not keep application state, create approval records, execute tools,
or spawn the Python runtime.

## Canonical routes

The allowlist is intentionally narrow:

- `POST /api/runs`
- `POST /api/intents/{intent_id}/execute`
- `GET /api/approvals`
- `GET /api/approvals/{approval_id}`
- `POST /api/approvals/{approval_id}/decision`
- `GET /api/executions/{execution_id}`
- `GET /api/experiments`
- `GET /api/experiments/{experiment_id}`
- `POST /api/experiments/{experiment_id}/evidence`
- `POST /api/experiments/{experiment_id}/evaluate`
- `GET /api/learning/context`

Unknown `/api/*` routes return `404` and never fall through to a legacy handler.

## Authentication forwarding

The BFF forwards the incoming `Authorization` header to Python. It does not
construct identity from `X-Principal`, `X-Role`, `X-Tenant-ID`, or similar
client-provided identity headers.

## Readiness

`GET /ready` probes the protected canonical `GET /api/approvals` surface and
forwards a caller-supplied `Authorization` header when present. A non-5xx
response, including the expected `401` for an anonymous probe, proves that the
Python S21 service is reachable; connection failures and 5xx responses report
the backend as unavailable. The BFF does not authenticate or mint a probe token.

## Process ownership

The BFF does not start or own the Python process. Deployment is expected to
manage the Python S21 service independently.
