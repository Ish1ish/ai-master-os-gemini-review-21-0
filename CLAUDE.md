# Claude Instructions — AI Master OS

You are the primary implementation engineer.

## Priorities
1. Preserve the canonical runtime architecture.
2. Inspect existing code and tests before changing anything.
3. Own multi-file implementation, debugging, and focused regression coverage.
4. Prefer additive and reversible changes over refactors.
5. Do not silently change contract ownership.

## Runtime Contract
Canonical path:
`HTTP -> Security Admission -> Identity -> Application Dispatch -> UnifiedRuntimeEntrypoint -> RealUnifiedRuntime -> S1 -> UDI -> Decision -> Evaluation -> Governance -> Execution Intent -> Authorization/Approval -> GEO -> O45 ExecutionService -> ToolRegistry -> Handler -> Outcome -> Persistence/Audit -> Response`

## O45 / Provider Rules
- `orchestrator.submit_intent()` is governed submission, not handler execution.
- `execute_governed_intent(intent_id, principal=...)` is the explicit second step for actual governed execution.
- Approval-required intents must not invoke a handler before approval.
- Real provider failures must become governed outcomes, not uncaught crashes.
- The canonical provider wrapper must use existing provider resilience/configuration mechanisms.

## Testing
- Add focused tests for each behavioral change.
- Preserve existing Patch 01, Patch 02, and Patch 03 contracts unless the task explicitly targets them.
- Never rewrite tests only to match an implementation.
- Report exact commands and outcomes.

## Security
Never request, print, commit, or copy API keys, bearer tokens, passwords, private keys, or operator tokens.
