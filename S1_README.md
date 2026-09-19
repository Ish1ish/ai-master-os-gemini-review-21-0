# 21.0 S1 — Intent → Understand → Route → Decision

This patch adds the first executable layer above Unified Runtime Contract v1.

Design boundary:
- deterministic IDs and trace propagation
- stage-local results
- fail-closed invalid adapter outputs
- advisory routing only
- no external side effects
- no governance mutation
- no memory mutation
- Decision stage is an adapter boundary, not a replacement for the existing Decision Intelligence engine

Apply the patch at the root of `07_WORKSPACE\21.0_Unified_End_to_End_User_Journey`.
