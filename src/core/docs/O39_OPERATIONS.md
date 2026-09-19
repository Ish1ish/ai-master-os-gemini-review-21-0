# O39 — Production Operations & Control Readiness

O39 is the operations layer on top of the O38-v1.8.0 production candidate. It does not change the semantic runtime chain. It adds a reproducible operator snapshot, release-freeze metadata, Windows verification, and a safer release gate that reads its version from the canonical manifest.

## Operational rules
- Do not print provider credentials, bearer tokens, or signing secrets.
- Do not run live provider calls from the operations snapshot.
- Treat the release manifest as the canonical version source.
- Preserve the current known-good artifact and persistent database snapshot before upgrades.
- Treat approval-pending state as governed state, not as a runtime failure.

## Windows verification
```cmd
set PYTHONPATH=%CD%
set PYTHONWARNINGS=error::ResourceWarning
scripts\windows_verify_o39.cmd
```

## Operator snapshot
```cmd
scripts\windows_ops_snapshot.cmd
```
The snapshot is read-only. It records release metadata, safe environment readiness, local SQLite integrity, and local API health/readiness if the API is running.

## Freeze criteria
A release is considered frozen when the Windows verification gate passes, the exact archive SHA-256 is recorded, and the previous production artifact is retained for rollback.
