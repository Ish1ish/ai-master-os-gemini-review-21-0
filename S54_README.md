# O45-S54 — Failure Learning & Adaptive Recovery

Consumes the bounded recovery outcome from S53 and turns it into a deterministic,
traceable learning signal and explicit next-decision route.

Properties:
- failure classification is deterministic
- evidence references are preserved
- recovered vs partial recovery are distinguished
- next decision is explicit
- replay is idempotent per recovery run id
- no AI-memory write
- no external action
- no automatic execution from the learning signal

This patch is intentionally a composition boundary over S53. It does not replace
provider recovery or alter provider credentials.
