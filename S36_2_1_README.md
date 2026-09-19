# O39 S36.2.1 — Real Provider Contract Classification Fix

The real providers returned successful-shaped payloads without a `status` key.
This patch classifies success from the actual current contract:
- model: dict with provider/model and exact smoke text `PROVIDER_SMOKE_OK`
- search: dict with a non-empty `results` list

Secrets and response bodies are never printed.
