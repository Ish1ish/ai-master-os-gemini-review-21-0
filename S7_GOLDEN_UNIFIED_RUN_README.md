# 21.0 S7 — Golden Unified Run

S7 verifies the cross-stage Unified Journey in one deterministic run:

INTENT
→ UNDERSTAND
→ ROUTE
→ DECISION
→ EVIDENCE
→ EVALUATION
→ GOVERNANCE
→ EXECUTION
→ OUTCOME
→ FEEDBACK
→ LEARNING
→ ADAPTATION
→ NEXT_DECISION

The dedicated S1/S2 suites already verify their internal adapters. S7 uses
canonical S1/S2 handoff envelopes and the real S3-S6 adapters to prove:
- one run_id/project_id survives the full chain;
- evaluation GO becomes governed execution;
- execution produces observable outcome evidence;
- outcome becomes feedback/learning/adaptation;
- adaptation produces an explicit next-decision route;
- no external action, governance mutation, or automatic memory write occurs;
- deterministic execution/learning identity is preserved.
