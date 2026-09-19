# O38 Go-Live Checklist

## Package
- Verify archive SHA-256 before deployment.
- Deploy the exact O38 archive; do not modify code after checksum verification.

## Secrets
- Inject `AI_OS_ENV=production`.
- Inject `AI_OS_IDENTITY_SIGNING_SECRET` from a secret manager; never commit it.
- Inject model/search endpoint URLs, API keys, model name, and DB paths.
- Confirm no secrets are present in shell history, source, or logs.

## Network
- API binds to `127.0.0.1:8080` or equivalent private interface.
- TLS terminates at the approved reverse proxy/load balancer.
- Public firewall rules expose only the intended TLS edge.
- Direct public access to the application port is denied.

## Security tests
- POST `/runs` without Authorization returns `401`.
- Tampered bearer returns `401` / unauthenticated.
- A valid signed bearer with the required scope can submit.
- Legacy principal-id-only credential is rejected.

## Providers
Run:
```bash
python scripts/staging_provider_smoke.py
```
The script must finish with `STAGING_PROVIDER_SMOKE_PASS` in the controlled staging environment.

## Persistence
- Run `scripts/backup_sqlite.py` for each persistent database.
- Move backup to protected storage according to the retention policy.
- Run `scripts/restore_verify.py` into an isolated restore location.
- Confirm application startup against the restored database where appropriate.

## Rollback
- Keep the prior production release archive and checksum.
- Stop API/worker cleanly.
- Restore previous release only after persistent-store compatibility is confirmed.
- Re-run health, readiness, authentication, and smoke checks before reopening traffic.

## Final sign-off
Record operator, date/time, target environment, certificate status, provider smoke result, backup/restore result, and rollback test result.
