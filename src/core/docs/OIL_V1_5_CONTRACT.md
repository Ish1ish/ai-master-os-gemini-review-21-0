# v1.5 Outcome Intelligence & Learning Contract

## Purpose

Convert v1.4 outcome evidence into deterministic, evidence-bound assessment and a bounded learning signal.

Flow:

Decision → Intent → Governance → Execution → Receipt → Outcome Evidence
→ Outcome Intelligence → Learning Signal → O43 context

## Outcome quality

- FULL_SUCCESS
- PARTIAL_SUCCESS
- MISSED_TARGET
- FAILED
- INCONCLUSIVE

## Target status

- MET
- PARTIAL
- MISSED
- UNKNOWN

## Decision quality

- SOUND_DECISION
- TARGET_MISSED
- EXECUTION_MISMATCH
- INSUFFICIENT_EVIDENCE
- UNRESOLVED

## Attribution

- DECISION
- EXECUTION
- ROUTING
- TOOL
- GOVERNANCE
- INSUFFICIENT_EVIDENCE

## Learning signal

- POSITIVE_CALIBRATION
- REFINE
- NEGATIVE_SIGNAL
- DO_NOT_LEARN

## Safety boundaries

1. Outcome Intelligence is read-only analytics over recorded evidence.
2. It never executes tools.
3. It never changes governance or approval state.
4. It never changes authorization.
5. It never mutates O43 history directly.
6. Missing/weak evidence produces DO_NOT_LEARN.
7. INCONCLUSIVE outcomes never drive the next decision.
8. Assessment IDs are deterministic for identical inputs.
9. Future outcomes are not inferred from a single observed run.

## v1.5 acceptance baseline

- deterministic assessment
- explicit expected/actual separation through target_status + v1.4 trace
- explicit outcome quality
- explicit decision quality
- explicit attribution
- explicit learning signal
- evidence sufficiency gate
- deterministic assessment identity
- fail-closed validation
