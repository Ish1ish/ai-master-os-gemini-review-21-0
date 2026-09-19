# S28 — Caddy Staging Config

Purpose:
Restore the canonical local HTTPS edge for the S21 staging server.

Canonical configuration:
- HTTPS listener: localhost:8443
- Internal TLS
- Reverse proxy target: 127.0.0.1:8091

Apply:
1. Copy `tools\caddy\Caddyfile` into the workspace at `tools\caddy\Caddyfile`.
2. Validate the config.
3. Start Caddy with the config.
4. Confirm TCP 8443 is LISTENING before running the HTTPS curl test.

This patch does not change S21, authentication, authorization, or runtime code.
