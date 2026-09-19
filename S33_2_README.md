# O39 / S33.2 — Async Startup Race Fix

S33.1 proved the PID/stop wiring but exposed a second operational issue:
S21 and Caddy are launched asynchronously, while the previous start wrapper checked listeners immediately.

S33.2 fixes that race by waiting for:
- 8091 after S21 start
- 8443 after Caddy start

The recovery gate also waits for both ports to disappear before restarting.

No secrets are printed.
This is staging recovery evidence only.
