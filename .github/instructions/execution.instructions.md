---
applyTo: "src/core/src/*execution*.py,src/core/src/governed_*.py,src/core/src/tool_registry.py,src/core/src/governance_intelligence.py"
---

# Governed Execution Rules

Preserve the distinction:
- `action` = business/risk classification.
- `tool_name` = technical ToolRegistry target.

Preserve the governed lifecycle:
intent creation -> governance -> authorization/approval -> governed execution service -> registered handler -> outcome -> persistence/audit.

A submitted or preflight-ready intent is not proof that a handler executed.

Approval-required actions must remain blocked/pending until valid approval exists.

Use existing receipt, observability, resilience, and persistence components rather than creating parallel stores.
