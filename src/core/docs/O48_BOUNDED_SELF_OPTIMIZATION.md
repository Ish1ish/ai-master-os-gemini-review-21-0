# v0.8 — Bounded Self-Optimization

## Purpose

v0.8 adds a policy-first self-optimization layer that can observe evidence, propose bounded changes, simulate them, evaluate expected impact, pass the result through governance, and record an explicitly approved reversible state transition.

## Safety boundary

- Simulation is side-effect free.
- Production auto-apply is disabled.
- Evidence references and rollback plans are mandatory.
- High-uncertainty simulation evidence forces `REFINE` rather than `GO`.
- Consequential changes remain under explicit governance review.
- Governance authority is not weakened by optimization logic.
- External actions are not executed by this component.
- Every applied change carries a version and previous-version reference for rollback.

## Lifecycle

`Observe → Propose Change → Simulate → Evaluate Expected Impact → Governance → Human/Policy Gate → Apply → Measure → Rollback`

## Deterministic decisions

- `GO`: all declared success metrics pass the threshold and uncertainty is not HIGH.
- `REFINE`: simulation evidence is too uncertain to justify a change.
- `NO-GO`: one or more success metrics fail.
- `REVIEW`: governance must decide a consequential or otherwise governed change.
- `SIMULATION_ONLY`: explicitly non-apply proposal.

## Non-goals

v0.8 does not implement unrestricted self-modification, live external execution, autonomous policy changes, or learning that can override governance.
