# O39 / S35 — Production Edge / Network Contract

Staging contract:
- Backend: 127.0.0.1:8091
- TLS edge: localhost:8443
- Direct public backend exposure: prohibited
- TLS edge: required

Gate checks:
1. Caddy configuration validates.
2. Backend listens on loopback.
3. TLS edge listens on 8443.
4. Both are locally reachable.
5. Contract records direct public backend exposure as disallowed.

Staging evidence only; no internet-facing production approval.
