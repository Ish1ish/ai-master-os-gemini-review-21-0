# O39-S37 Provider Reliability & Failure Governance

This milestone hardens the live-provider boundary with:

- bounded retries for transient transport failures, HTTP 429, and HTTP 5xx;
- Retry-After support when supplied by the provider;
- non-retryable 4xx fail-closed behavior;
- per-provider in-process circuit breaker with cooldown / half-open recovery;
- preserved provider error metadata without exposing credentials;
- targeted reliability regression tests;
- staging evidence gate with explicit no-external-action and no-memory-write assertions.

## Apply

Extract the patch into the project root so it overlays:

- `src/core/src/provider_resilience.py`
- `src/core/src/live_providers.py`
- `tests/test_s37_provider_reliability.py`
- `scripts/s37_provider_reliability_gate.py`
- `S37_README.md`

## Gate

Run:

`python scripts/s37_provider_reliability_gate.py`

Expected final marker:

`S37_PROVIDER_RELIABILITY_PASS`

The gate is deterministic and uses injected failure scenarios for reliability behavior. It does not perform consequential external actions or write runtime memory.


S37.1 Test Runner Independence: targeted reliability tests run directly with Python, without requiring pytest. The gate uses the native test runner and remains fail-closed.
