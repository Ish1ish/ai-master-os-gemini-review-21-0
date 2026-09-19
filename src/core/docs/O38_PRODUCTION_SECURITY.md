# O38 Production Security & Live Deployment Hardening

## Scope
O38 closes the final network/authentication boundary gaps identified in the O37 readiness review.

## Controls
- Production mode requires `AI_OS_IDENTITY_SIGNING_SECRET`; development fallback is disabled.
- Sensitive HTTP routes require O36 signed bearer credentials.
- Health/readiness endpoints stay probe-friendly.
- Production API binds to loopback in the bundled service example.
- TLS terminates at the trusted edge; the application is not directly internet-facing.
- Production secrets are externalized.
- Legacy principal-id-only authentication remains rejected.

## Remaining operational gate
Real-provider staging, backup/restore, rollback, and firewall validation require the target deployment environment and real provider credentials and therefore cannot be truthfully marked complete inside this portable package.
