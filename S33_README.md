# O39 / S33 — Recovery + Restart Gate

Purpose:
Prove that the S32 operational controls support a clean stop/restart cycle and that the authenticated HTTPS path remains healthy after restart.

Gate:
1. Pre-check operational status.
2. Stop S21/Caddy through the controlled operations wrapper.
3. Confirm 8091 and 8443 are no longer listening.
4. Start through the controlled operations wrapper.
5. Re-run operational status checks.
6. Re-run the live HTTPS authenticated admission check.

The bearer token is loaded from staging\operator_token.txt and never printed.

This is a staging recovery/restart gate.
It does not grant internet-facing production approval.
