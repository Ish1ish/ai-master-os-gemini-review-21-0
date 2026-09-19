# 21.0 S8 — Persistent Trace + Memory Handoff

S8 takes the verified Golden Unified Run and adds two controlled persistence
boundaries:

1. UnifiedRunPersistence
   - compact structured JSONL trace
   - deterministic fingerprint
   - same-run idempotent replay
   - true identity conflict detection
   - project-scoped lookup

2. UnifiedMemoryHandoff
   - creates a reviewable structured memory proposal
   - carries lesson / confidence / next decision / adaptation
   - NEVER commits memory automatically
   - explicitly marks human_gate=True

This is intentionally aligned with the Memory Runtime principle that memory is
structured operational state with source, scope, version/confidence/lifecycle
rather than a chat transcript dump.
