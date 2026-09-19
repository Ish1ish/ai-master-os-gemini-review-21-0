
# O39 S36.2 — Real Provider Staging Gate

Uses the actual current Unified runtime provider surface:
- `core.src.live_providers.provider_configuration_status()`
- `core.src.live_providers.model_provider(prompt)`
- `core.src.live_providers.search_provider(query)`

The gate is secret-safe:
- never prints API keys
- never prints bearer tokens
- never prints provider response bodies
- stores only result shape and SHA-256 digest of returned Python objects
- records external_action_executed=false and memory_write_executed=false

Exit codes:
0 = real model + real search both passed
1 = provider call/import/contract failure
2 = required provider environment is not configured

Expected successful marker:
`S36_2_REAL_PROVIDER_STAGING_PASS`

Evidence:
`staging\s36_2_real_provider_staging.json`
