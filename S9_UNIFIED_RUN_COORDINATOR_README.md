# 21.0 S9 — Unified Run Coordinator

S9 turns the verified S1-S8 pieces into one host-level coordinator call.

Pipeline:
GoldenUnifiedRun
    -> Persistent Unified Run Trace
    -> Reviewable Memory Proposal

The coordinator does not add a second execution engine or second memory store.
It simply composes the canonical journey and the controlled persistence
boundaries already verified in S1-S8.

Safety:
- no external action is enabled;
- no automatic memory write occurs;
- same run identity is idempotent;
- true identity conflicts remain visible;
- project isolation is preserved.
