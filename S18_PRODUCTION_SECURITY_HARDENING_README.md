# S18 / O38 — Production Security & Live Deployment Hardening

This stage makes production security requirements explicit and fail-closed.

## Added contract

- `AI_OS_RUNTIME_MODE=production` requires `AI_OS_IDENTITY_SIGNING_SECRET`.
- Production mode requires authentication and TLS at the deployment boundary.
- External actions remain disabled by this layer.
- Automatic memory write remains disabled by this layer.
- Unknown runtime modes fail closed.

## Boundary

This patch does **not** expose a network service, provision infrastructure, inject real provider credentials, or claim that an external environment has been verified. It is the contract we will connect to the server/startup and deployment layer next.

## Verification

Run the targeted S18 suite, the full regression suite, and `compileall` from the current workspace.
