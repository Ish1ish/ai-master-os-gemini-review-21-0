# O38 Staging Deployment Runbook

This gate is intentionally evidence-bound. It does not claim that a target host,
TLS endpoint, Tavily, OpenRouter, or backup system has been verified merely because
the local tests pass.

## Required deployment shape

Internet / client -> TLS edge or reverse proxy -> private AI Master OS HTTP service.
The backend listener must not be directly exposed to the public network.

## Required staging secrets

- `AI_OS_IDENTITY_SIGNING_SECRET`
- `TAVILY_API_KEY`
- `OPENROUTER_API_KEY`

Never print their values. Inject them from the deployment secret manager.

## Staging acceptance evidence

1. Start the HTTP service on a private listener.
2. Terminate TLS at the trusted edge and route the staging hostname to the service.
3. Run unauthenticated, invalid-token, TLS-disabled/direct-path, and allowed-request HTTP checks.
4. Run a controlled real-provider smoke with the real staging credentials.
5. Execute backup and restore against the actual persistent state location.
6. Record the exact outputs before declaring GO-LIVE READY.

A successful local unit suite is necessary but not sufficient for production readiness.
