# AI Master OS UI v4.0.0 — Final Test Candidate

V4 is the master UI target release for the current core runtime. It consolidates the Control Center direction into one backend-connected surface.

## Non-negotiables
- Backend is the source of truth for durable runtime state.
- UI uses the authenticated same-origin /api proxy.
- No fake live governance, policy, approval, execution or recovery state.
- Clear History clears only browser-local run index.
- Arabic is a first-class language option and switches the interface to RTL.
- Human governance remains in force for consequential external actions.

## Verification
Run `scripts\windows_ui_v40_verify.cmd` from the V4 root.
