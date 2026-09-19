# Strategy Adaptation Intelligence v2.0 Contract

Purpose: transform attributable v1.9 Strategy Feedback signals into a project-scoped advisory adaptation context for subsequent strategy decisions.

Boundaries:
- Descriptive historical rates are evidence summaries, not probabilities or guarantees.
- DO_NOT_LEARN feedback is ignored for adaptation.
- EXECUTION, TOOL, and GOVERNANCE attribution remain outside strategy blame.
- Fewer than 3 attributable feedback items or evidence < 0.70 routes to COLLECT_MORE_EVIDENCE.
- ELEVATED_CAUTION and INVESTIGATE_EXECUTION posture are preserved; adaptation cannot lower governance.
- No external action is executed.
- O43 memory is not mutated directly.
- Persistence is local and idempotent; true ID conflicts fail closed.

Recommendations:
- MAINTAIN_STRATEGY
- EXPLORE_ALTERNATIVE
- REFINE_STRATEGY
- COLLECT_MORE_EVIDENCE
