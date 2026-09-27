# S21 HTTP Composition Patch

Adds a thin launcher/composition boundary for the existing canonical S21 HTTP server.

## Authority

- Security remains `ProductionSecurityConfig` + S19/S20 boundary.
- Identity remains the O36 signed-bearer authenticator.
- Runtime authority remains `UnifiedRuntimeEntrypoint` / `RealUnifiedRuntime`.
- Routing remains `CanonicalHTTPAPI`.
- External actions and automatic memory writes remain disabled.

## Start

From the repository root:

`python -m pip install --editable . --no-deps`

`python -m unified_runtime.s21_http_launcher`

The editable install makes the repository's `src` packages discoverable without
per-command `PYTHONPATH` setup.

Environment variables:

- `AI_OS_RUNTIME_MODE`
- `AI_OS_IDENTITY_SIGNING_SECRET`
- `AI_OS_TLS_TERMINATED_BY_EDGE`
- `AI_OS_S21_HOST`
- `AI_OS_S21_PORT`
- `AI_OS_UNIFIED_RUNTIME_PERSISTENCE_ROOT`

Default port is `8091`.
