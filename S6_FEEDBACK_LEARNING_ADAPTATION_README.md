# 21.0 S6 — Feedback → Learning → Adaptation Integration

S6 closes the learning side of the Unified Runtime:

OUTCOME → FEEDBACK → LEARNING → ADAPTATION → NEXT DECISION

Decision-driving semantics:
- SUCCESS -> POSITIVE_STRATEGY_SIGNAL -> MAINTAIN_STRATEGY
- FAILURE -> NEGATIVE_STRATEGY_SIGNAL -> EXPLORE_ALTERNATIVE
- BLOCKED -> INCONCLUSIVE_SIGNAL -> COLLECT_EVIDENCE

Important boundary:
- A blocked execution is not treated as evidence that the strategy failed.
- The adapter does not write memory automatically.
- The adapter does not mutate O43 or strategy state automatically.
- Adaptation is authoritative for routing, not autonomous external action.
- Every learning envelope is deterministic and traceable to run/project/strategy/execution.
