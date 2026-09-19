# S31 — Freeze + Evidence Manifest + Release Candidate

Purpose:
Freeze the verified O38 staging state into a reproducible release-candidate evidence bundle.

The gate records:
- Full regression result
- compileall result
- S21 listener on 8091
- Caddy listener on 8443
- Live HTTPS authenticated admission result
- A concise release-candidate manifest

The operator token is read from `staging\operator_token.txt` and is never printed.

This is a staging release-candidate freeze only.
It does NOT approve direct internet-facing production deployment.
