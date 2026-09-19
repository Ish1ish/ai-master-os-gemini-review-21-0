# 21.0 S1 — UnifiedDecisionIntelligence Integration

This patch connects the existing Unified Runtime S1 DECISION stage to the
existing `UnifiedDecisionIntelligence.plan()` implementation.

Import boundary:
- Existing UDI source remains under `src\core\src`.
- Runtime uses `PYTHONPATH=%CD%\src;%CD%\src\core\src;%CD%`.
- No copy or fork of `unified_decision_intelligence.py` is created.

Behavioral boundary:
- UDI remains advisory-only.
- Existing UDI statuses are preserved: RECOMMEND / REFINE / HOLD.
- UDI plan_id remains authoritative and deterministic.
- Governance remains authoritative.
- External actions remain false.
- S1 trace/run identity remains owned by Unified Runtime Contract.
