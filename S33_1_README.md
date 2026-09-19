# O39 / S33.1 — Recovery Restart Wiring Fix

S33 exposed a real operational defect: the S29 launcher did not preserve the S21 PID file used by the O39 stop wrapper, so the S33 stop phase could leave 8091 running.

S33.1 restores an explicit PID file in the S21 server and adds a port-based fallback to the stop wrapper.

The recovery gate:
- stops S21 and Caddy,
- proves 8091 and 8443 are down,
- starts the stack through the O39 wrapper,
- checks both listeners,
- verifies live authenticated HTTPS admission.

This is staging recovery evidence only.
