# O43 — Learning & Decision Memory Loop

## Purpose
Turn concluded O42 experiment outcomes into bounded, retrievable decision context for the next cycle.

**Experiment → Evidence → Decision → Lesson → Retrieve → Next Decision**

## Scope
- project-scoped learning context derived from concluded experiments;
- deterministic routing guidance: bounded next step, refine, or route to next hypothesis;
- retrieval that excludes inconclusive experiments and requires evidence references;
- durable context identifiers for auditability;
- no automatic external action and no silent rewrite of prior decisions.

## Decision semantics
- `GO`: prior evidence supports a bounded next step;
- `REFINE`: change one material variable before another test;
- `NO-GO`: do not repeat the same hypothesis unchanged; route to another ranked hypothesis;
- `INCONCLUSIVE`: retained as observation but excluded from decision-driving learning context until evidence is complete.

## API
- `GET /learning/context?project_id=PROJ-001`
- optional `experiment_id` excludes the current experiment from retrieved context.

## Memory boundary
Memory is operational state, not transcript storage. Retrieved lessons retain experiment IDs, decisions, confidence, sample size, metrics, next steps, and evidence references. Prior outcomes are evidence for routing, not proof of future success.
