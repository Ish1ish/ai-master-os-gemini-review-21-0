# O45-S50 — Decision Loop Re-entry

S50 consumes the S49 persisted outcome trace and turns its `next_decision` into an explicit, reviewable context for the next decision cycle.

## Contract

`S46 execution -> S47 outcome -> S48 integration -> S49 persisted trace -> S50 decision-loop re-entry`

The re-entry context carries:
- source trace id/version
- project/action identity
- outcome status
- next decision
- decision feedback
- evidence refs
- stable loop id/version

## Safety boundary

S50 does not execute the next action, write AI memory, enable external effects, or grant production approval. Re-entry is a decision-context boundary only; a later governed execution path must explicitly authorize any new consequential action.

## Verification

Run the native targeted tests, then the S50 gate. The gate also runs compileall.
