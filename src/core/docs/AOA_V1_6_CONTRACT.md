# AI Master OS v1.6 — Advanced Outcome Analysis Contract

## Purpose

v1.6 aggregates already-recorded v1.5 Outcome Intelligence assessments across a bounded project-scoped window.

The purpose is to identify repeated patterns, distinguish decision-side from execution-side problems, quantify evidence coverage, and produce an advisory route for a later controlled learning-to-policy phase.

## Input

v1.5 assessments containing at minimum:

- `assessment_id`
- `project_id`
- `target_status`
- `outcome_success`
- `outcome_quality`
- `decision_quality`
- `attribution`
- `learning_signal`
- `evidence_sufficient`

## Output

Schema: `AOA-v1.0`

The analysis contains:

- deterministic `analysis_id`
- bounded `sample_size`
- evidence sufficiency rate
- eligible learning sample
- target/outcome/decision/attribution/signal distributions
- eligible success rate
- decision miss rate
- execution mismatch rate
- trend: `IMPROVING | STABLE | DETERIORATING | UNKNOWN`
- findings / repeated-pattern flags
- advisory route:
  - `MAINTAIN`
  - `REFINE_DECISION`
  - `INVESTIGATE_EXECUTION`
  - `COLLECT_MORE_EVIDENCE`
  - `MONITOR`
- confidence
- exact assessment references

## Pattern rules

v1.6 deliberately uses deterministic heuristic thresholds, not probabilities.

- Repeated decision misses: eligible miss rate >= 0.40 with at least 3 eligible assessments.
- Repeated execution mismatch: execution mismatch rate >= 0.30 with at least 3 evidence-sufficient assessments.
- Weak evidence coverage: evidence sufficiency rate < 0.70.
- Unknown-target pattern: target `UNKNOWN` >= 0.30 of the analysis window.
- Positive calibration pattern: at least 60% of an eligible sample, with at least 3 eligible assessments.

These are prioritization thresholds. They are not claims of causality.

## Boundaries

v1.6:

- does not execute tools or external actions
- does not modify governance or authorization
- does not approve actions
- does not mutate O43 memory
- does not convert one observed run into a future guarantee
- remains project-scoped
- remains deterministic and replay-safe

## Intended next phase

v1.7 can consume repeated pattern findings to propose bounded policy/routing improvements under existing governance controls.

v1.6 itself only observes, summarizes, and recommends an advisory route.
