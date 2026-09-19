# O38 Production Security & Live Deployment Hardening

Public traffic MUST terminate TLS at a trusted edge and proxy to the API on loopback/private networking. Do not bind the application API directly to `0.0.0.0` in production.

Required production environment: `AI_OS_ENV=production`, `AI_OS_IDENTITY_SIGNING_SECRET`, model/search provider variables, and persistent DB paths. Secrets are injected externally and never committed to the package.

The application enforces the O36 signed-bearer boundary on sensitive HTTP endpoints. `/health` and `/readiness` remain unauthenticated for orchestration probes.

Recommended topology:

```text
Internet -> TLS reverse proxy/load balancer -> 127.0.0.1:8080 (O38 API)
                                      \-> worker process -> persistent DBs
```

Before go-live, execute:
1. staging provider smoke with real externally injected credentials;
2. backup + restore drill;
3. rollback drill;
4. firewall test proving the application port is not publicly reachable.
