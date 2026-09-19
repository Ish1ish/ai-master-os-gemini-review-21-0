# UI11-O46 — Live Golden Run Inspector

Connects the UI10 Golden Experience to a GET-only live backend inspection surface.

Scope:
- Select a recent real backend run.
- Rehydrate the canonical O46 experience view for that run.
- Validate intent, research, decision, governance, approval, outcome, learning and next-decision coherence.
- Show a user-facing integrity banner with PASS/CHECK state.
- Keep inspection read-only; no POST/PUT/DELETE is issued by UI11.
- Responsive and mobile-friendly.

Validation:
- test_o46_golden_live_inspector.py
- ui11_o46_golden_live_inspector_gate.py
- compileall
