
# O39 S36.3 — Runtime Provider Wiring Gate

This gate verifies the current Unified workspace wiring without making external provider calls.

Checks:
1. `core.src.service` imports the live model/search providers.
2. The service source passes those providers into its runtime construction.
3. The service module provider objects are the same objects exported by `core.src.live_providers`.
4. `core.src.real_wiring.O23Runtime` accepts injected model/search providers.
5. The injected providers become the runtime prompt and market provider callables.

No API keys, tokens, provider responses, memory writes, or external actions are printed or executed.

Expected marker:
`S36_3_RUNTIME_PROVIDER_WIRING_PASS`
