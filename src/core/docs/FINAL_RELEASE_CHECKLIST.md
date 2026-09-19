# AI Master OS O40 — Final Release Checklist

## Automated / local
- Full unittest suite passes with `PYTHONWARNINGS=error::ResourceWarning`.
- `compileall` passes.
- Existing O38 offline quality gate passes.
- O40 final gate passes locally.
- Release manifest and checksum are frozen.
- Isolated backup/restore rollback rehearsal passes.

## Target environment — manual evidence
Provide four text evidence files under an operator-controlled evidence folder:

- `firewall_public_port.txt` — proof that TCP/8080 is not Internet-exposed and only the intended TLS edge is reachable.
- `tls_certificate.txt` — certificate issuer/expiry/hostname and rotation test outcome. Do not include private keys.
- `backup_restore.txt` — retention schedule, encrypted backup location, and successful restore result.
- `rollback_execution.txt` — exact prior-release artifact, checksum, rollback timestamp, and successful service recovery.

## Release decision
`READY` requires no failed checks and all target-environment evidence present.
`CONDITIONAL` means the packaged system is locally healthy but one or more target-environment checks remain manual.
`NOT_READY` means at least one automated or supplied evidence check failed.

The release is not considered Internet-facing production-ready solely because the local Windows gate passes.
