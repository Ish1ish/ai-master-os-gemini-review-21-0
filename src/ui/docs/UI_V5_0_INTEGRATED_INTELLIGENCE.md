# UI Console v5.0.1 — Integrated Intelligence Visual QA Hardening

This UI revision unifies the existing v4.6 control center with the Strategy Intelligence → Strategy Feedback → Strategy Adaptation chain.

## Boundaries
- Backend-authoritative state only.
- Read-only adaptation bridge.
- No UI-created approvals.
- No external action from adaptation.
- No silent O43 mutation.
- Weak evidence remains visible and does not become confident adaptation.

## Data path
Decision → Outcome → Strategy Feedback (v1.9) → Strategy Adaptation (v2.0) → Next Decision context.

## Local bridge
The console exposes `GET /api/strategy/adaptation`. It reads the v1.9 `strategy_feedback` SQLite store and derives the v2.0 context using the real `StrategyAdaptationIntelligence` implementation. It never writes feedback or adaptation state.

Set `AI_OS_STRATEGY_FEEDBACK_DB` to the authoritative feedback database path when it is not located at the default local data path.


## Visual QA hardening
- Stabilized the sidebar/main grid contract for LTR and RTL to prevent content overlap.
- Removed the top-level search field and refresh control from the primary toolbar while preserving compatibility hooks.
- Reworked the toolbar into grouped runtime/language and operator/session controls.
- Reframed runtime status wording so a healthy runtime is not contradicted by an unavailable optional endpoint.
- Added compact, explicit empty/unavailable/error state treatments.
- Reduced dashboard dead space and simplified the governed-run entry flow with an advanced context section.
- Collapsed secondary System navigation and auto-opened it when deep-linking into a system page.
- Added responsive and RTL structural hardening.
