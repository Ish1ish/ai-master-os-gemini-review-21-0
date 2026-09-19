# O39 Release Freeze

## Current candidate
- Package: O39-v1.0.0
- Base runtime: O38-v1.8.0
- UI candidate: v0.9.0
- Scope: operational readiness only; semantic runtime behavior remains locked.

## Freeze evidence
1. Windows verification passes.
2. Offline quality gate passes.
3. Compile check passes.
4. Release manifest is internally consistent.
5. Exact archive SHA-256 is recorded.
6. Prior known-good archive is retained.
7. No secrets are bundled.

## Change policy after freeze
Changes to engine contracts, semantic handoffs, provider behavior, or governance policy require a new release candidate and full regression verification.
