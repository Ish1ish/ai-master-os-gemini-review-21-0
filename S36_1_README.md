# O39 S36.1 — Live Provider Adapter Alignment / Discovery

Purpose:
- Replace the incorrect O24-era imports used by the first S36 attempt.
- Discover the actual callable surface of the current `core.src.live_providers` module.
- Record only secret-safe metadata.
- Do not print API keys, tokens, URLs containing credentials, or provider response bodies.

Expected result:
`S36_1_PROVIDER_ADAPTER_DISCOVERY_PASS`

Evidence file:
`staging\s36_1_provider_adapter_inventory.json`

This stage is intentionally discovery/alignment only.
It does not call external model/search providers.
A subsequent S36.2 gate will use the discovered live-provider contract for real staging calls.
