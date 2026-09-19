# S11 — Unified Runtime Entrypoint

Adds a stable request-shaped host boundary over the verified S10 RealUnifiedRuntime.

Properties:
- accepts a typed request or mapping payload;
- validates required identity and mapping-shaped fields;
- preserves the canonical 13-stage runtime and S10 authoritative engines;
- fails closed on malformed input or runtime exceptions;
- keeps external action, governance mutation, and automatic memory write disabled;
- preserves deterministic persistence and idempotent replay.

This is an API/host boundary only. It does not add autonomous external execution.
