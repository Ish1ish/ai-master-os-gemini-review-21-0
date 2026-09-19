# O39-S36.5.1 — AI Runtime Live Text Contract Fix

Fixes the structured-generation contract so provider envelopes of the form `{provider, model, text}` parse the `text` payload as JSON instead of treating the envelope metadata as the model result. Invalid text remains fail-closed and uses existing retry policy.
