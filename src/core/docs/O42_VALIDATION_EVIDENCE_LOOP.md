# O42 — Validation & Evidence Loop

## Purpose
Turn an O41 decision surface into a durable, measurable experiment loop.

**Hypothesis → Experiment → Evidence → Evaluate → GO / REFINE / NO-GO → Learn → Remember → Re-run**

## Scope
O42 adds:
- durable experiment registry in SQLite;
- machine-readable success thresholds, while preserving O41 legacy text thresholds;
- evidence recording with explicit evidence references;
- deterministic evaluation with confidence and decision boundaries;
- durable conclusion + learning payload;
- authenticated API surfaces for listing, creating, recording evidence, and evaluating experiments.

## Safety
O42 does not perform external consequential actions. It records and evaluates evidence only. Publication, financial actions, messages, and other external effects remain behind the existing human governance gate.

## API
- `POST /experiments/from-run`
- `GET /experiments`
- `GET /experiments/{experiment_id}`
- `POST /experiments/{experiment_id}/evidence`
- `POST /experiments/{experiment_id}/evaluate`

## Decision semantics
- `GO`: planned sample complete and all success thresholds pass.
- `REFINE`: planned sample complete, but one or more success thresholds miss and no no-go threshold fires.
- `NO-GO`: an explicit no-go threshold fires.
- `INCONCLUSIVE`: sample or evidence references are incomplete.

## Evidence rule
An experiment cannot become decision-grade without evidence references. A result without traceable evidence is retained as an observation but returns `INCONCLUSIVE`.
