# 21.0 S4 — Governance Integration

S4 maps the canonical S3 EVALUATION result to a deterministic governance posture.

Decision mapping:
- GO -> PROCEED_TO_EXECUTION_GATE
- REFINE -> REFINE_BEFORE_EXECUTION
- NO-GO -> DO_NOT_PROCEED
- INCONCLUSIVE -> HOLD_FOR_MORE_EVIDENCE

Safety boundary:
- External action is never enabled by S4.
- No external action is executed.
- No governance state is mutated.
- Consequential execution approval remains a later gate.
- Invalid or incomplete evaluation fails closed.
