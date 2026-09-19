# v1.9 Strategy Feedback Intelligence Contract

Purpose: turn observed outcome evidence into an advisory signal about the selected strategy.

Signals: POSITIVE_STRATEGY_SIGNAL, NEGATIVE_STRATEGY_SIGNAL, REFINE_STRATEGY, DO_NOT_LEARN.
Routes: MAINTAIN_STRATEGY, REFINE_STRATEGY, COLLECT_MORE_EVIDENCE.

Evidence rules:
- INCONCLUSIVE or INSUFFICIENT_EVIDENCE never becomes a learning signal.
- sample_size < 3 never becomes a learning signal.
- EXECUTION, TOOL, or GOVERNANCE attribution does not blame strategy selection.
- Strategy feedback requires attributable DECISION or ROUTING evidence.

Boundaries:
- Governance remains authoritative.
- No external action is executed.
- No authorization is created or changed.
- No direct O43 memory mutation occurs.
- Local persistence is idempotent.
