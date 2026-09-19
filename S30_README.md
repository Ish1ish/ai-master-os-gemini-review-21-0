# S30 — Staging Evidence + Release Gate

Purpose:
Produce a reproducible staging evidence bundle after the S29 live authenticated HTTPS proof.

The gate performs, in order:
1. Full Python regression suite.
2. compileall for src and tests.
3. Live HTTPS POST through Caddy -> S21.
4. Checks that the live response is HTTP 200, authenticated=true, status=ADMITTED, external_action_executed=false, and memory_write_executed=false.

Evidence is written under:
`staging\release_gate\`

The operator token is loaded from:
`staging\operator_token.txt`

The token is never printed by this script.

Pass condition:
All commands return success and all live-response assertions pass.

This gate is staging evidence only. It does not approve direct internet-facing production deployment.
