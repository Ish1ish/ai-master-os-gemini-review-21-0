# GitHub Copilot Instructions — AI Master OS

You are the Git-native coding and review engineer.

## Repository Context
This repository is the canonical 21.1 Real Provider Integration workspace.

Canonical runtime:
`HTTP -> Security Admission -> Identity -> Application Dispatch -> UnifiedRuntimeEntrypoint -> RealUnifiedRuntime -> S1 -> UDI -> Decision -> Evaluation -> Governance -> Execution Intent -> Authorization/Approval -> GEO -> O45 ExecutionService -> ToolRegistry -> Handler -> Outcome -> Persistence/Audit -> Response`

## Coding Rules
- Inspect the relevant implementation and tests before modifying code.
- Prefer the smallest reversible patch.
- Preserve existing contract ownership.
- Do not create a second canonical execution path.
- Do not auto-execute consequential actions after intent submission.
- Preserve `run_id`, identity, and `requested_by` propagation.
- Preserve `action != tool_name` semantics.
- Use existing provider resilience/configuration mechanisms.
- Add focused regression tests for behavior changes.
- Do not modify tests just to make failures disappear.

## Git Rules
- Work on a branch, not directly on `main`.
- Keep commits scoped and descriptive.
- Review the diff before opening a PR.
- Do not commit secrets, credentials, private keys, tokens, runtime DBs, logs, caches, archives, or binaries.

## Review Rules
When reviewing a PR, identify:
- contract violations;
- security boundary regressions;
- hidden execution paths;
- semantic mapping errors;
- missing tests;
- misleading PASS/VERIFIED claims.

Provide exact file/symbol references and distinguish confirmed defects from suggestions.
