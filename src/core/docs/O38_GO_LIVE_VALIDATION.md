# O38 Go-Live Validation

This is the last gate before live traffic. It does **not** replace provider credentials, TLS issuance, firewall validation, backup retention, or an operator rollback exercise. Those are target-environment evidence.

## Windows
From the O38 project root:

```cmd
set "PYTHONPATH=%CD%"
set "PYTHONWARNINGS=error::ResourceWarning"
set "AI_OS_O38_ARCHIVE=C:\path\to\AI_Master_OS_O38_Production_Security_Hardening_v1.0.0.zip
set "AI_OS_PRIOR_ARCHIVE=C:\path\to\previous-production-release.zip
scripts\windows_go_live_verify_o38.cmd
```

The wrapper first runs the O38 security gate, then the executable go-live gate. It fails closed on any unexpected non-zero gate exit.

### Outcomes

- `READY` = all automated checks passed and no manual evidence remains.
- `CONDITIONAL` = automated checks pass, but infrastructure or provider evidence is still missing.
- `NOT_READY` = at least one automated safety check failed.

## Required target-environment evidence

1. `STAGING_PROVIDER_SMOKE_PASS` with real externally injected model/search credentials.
2. Public TLS edge is active with an approved certificate.
3. Public firewall exposes only the approved TLS entry point; direct `:8080` access is denied.
4. Backup/restore drill succeeds for each existing persistent database, with retention/encryption policy applied.
5. Previous release archive and checksum are available, and the rollback procedure has been exercised before reopening traffic.
6. Record operator, UTC timestamp, environment, certificate status, provider smoke result, backup/restore result, and rollback result.

The gate never prints secret values.
