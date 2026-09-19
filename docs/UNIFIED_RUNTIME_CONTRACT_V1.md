# Unified Runtime Contract v1

## Purpose
Provide one deterministic lifecycle state model shared by the next end-to-end integration work.

## Canonical stages
Intent → Understand → Route → Evidence → Decision → Evaluation → Governance → Execution → Outcome → Feedback → Learning → Adaptation → Next Decision.

## Safety boundary
A stage can start only after its predecessor succeeds. Unknown or out-of-order transitions fail closed. Terminal states are FAILED, BLOCKED, and CANCELLED.

## Scope
This contract is intentionally orchestration-neutral. It does not execute providers, mutate governance policy, perform external actions, or write O43 memory by itself. It establishes state, ordering, trace propagation, deterministic run identity, and a snapshot contract.
