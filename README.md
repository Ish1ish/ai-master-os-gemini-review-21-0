# O46 Golden Control + Golden Experience Fix

Purpose: repair the post-canonical-cleanup gap where `goldenCreateBtn`, `goldenExecuteBtn`, and `goldenInspectBtn` remained in `index.html` but their old UI15 event handlers were removed with the legacy overlay.

Also hydrates the Golden Experience page with safe backend-derived state and explicit empty/error-safe states.

Safety:
- Create is explicit user action.
- Execute is a separate explicit user action.
- No automatic execution on boot.
- UI never becomes governance authority.
- No secrets are rendered.

Install:
1. Extract this ZIP into the workspace root.
2. Run `python patch\apply_o46_golden_control_experience_fix.py` from the extracted folder.
3. Run the included targeted test from `src\core` with `PYTHONPATH=.` using the usual workspace layout.
