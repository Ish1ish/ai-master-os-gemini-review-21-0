# S19 — Production Security Boundary Wiring

S19 connects the S18/O38 production security contract to request admission.

## What it adds

- Explicit request admission boundary for production/staging/development modes.
- Production fails closed without an authenticator.
- Production requires TLS at the deployment edge.
- Production requires a non-empty bearer token and successful authentication.
- Authenticator failures fail closed.
- External actions and automatic memory writes remain blocked.
- Development mode keeps a clearly labeled local-only authentication bypass.

## Boundary

This patch does **not** start an HTTP server, expose a network port, perform provider calls, or claim target-environment verification. It is the application-layer admission contract that a real HTTP/server adapter will call next.

## Verification

Run the targeted S19 suite, full regression, and compileall.
