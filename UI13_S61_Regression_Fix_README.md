# UI13 regression fix

O46 UI13 Golden Run Control originally appended its implementation inside app.js after the UI12 Product Acceptance implementation. The existing UI12 regression contract inspects a bounded source slice and correctly rejected seeing UI13 POST methods inside that acceptance function boundary.

Fix:
- isolate UI13 Golden Run Control implementation into `src/ui/ui/golden_run_control.js`
- load it after `app.js` in `index.html`
- keep the app.js compatibility marker
- update UI13 targeted tests to validate the isolated implementation file
- preserve explicit user-initiated create and execute behavior

Validation performed in the patch workspace:
- UI13 Golden Run Control tests: 12/12 PASS
- UI12 Product Acceptance regression tests: 9/9 PASS
- compileall: PASS

No runtime policy, approval, execution, or memory semantics were changed by this overlay.
