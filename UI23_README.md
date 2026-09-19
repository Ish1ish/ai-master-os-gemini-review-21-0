# UI23 — O46 Structural Surface Repair

Purpose: remove the stray duplicated Recovery/Reconciliation markup in `src/ui/ui/index.html` that leaked into unrelated SPA pages such as Golden Run Control.

Scope:
- Repair malformed Recovery page boundary.
- Remove the exact duplicate Reconciliation Playbook block outside `#page-recovery`.
- Add a structural marker for regression detection.
- No backend changes, no API calls, no mutations, no governance changes.

Verification: `python scripts\\ui23_structural_surface_gate.py`
