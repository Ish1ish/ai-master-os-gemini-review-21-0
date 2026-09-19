# O39 / S36 — Real Provider Staging Gate

Purpose:
Validate the real model and search provider adapters against the provider credentials/configuration already injected into the staging environment.

Inputs are read only from environment variables:
- AI_OS_MODEL_BASE_URL
- AI_OS_MODEL_API_KEY
- AI_OS_MODEL_NAME
- AI_OS_SEARCH_BASE_URL
- AI_OS_SEARCH_API_KEY
- AI_OS_REQUEST_TIMEOUT_S

The gate never prints or stores API keys, authorization headers, model response content, or search result content.

Checks:
1. Required model/search configuration exists.
2. Real production model adapter executes a minimal structured probe.
3. Real production search adapter returns at least one result.
4. Evidence records status/provider/model name/result count/latency only.

This is a controlled staging smoke. It does not approve direct internet-facing production.
