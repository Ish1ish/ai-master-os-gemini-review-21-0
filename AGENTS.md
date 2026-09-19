# AI Master OS — Agent Collaboration Contract

## Project
Repository: `ai-master-os-gemini-review-21-0`
Workspace: `21.1_Real_Provider_Integration`

This repository is the canonical 21.1 Real Provider Integration workspace.

## Canonical Runtime Path
`HTTP -> Security Admission -> Identity -> Application Dispatch -> UnifiedRuntimeEntrypoint -> RealUnifiedRuntime -> S1 -> UDI -> Decision -> Evaluation -> Governance -> Execution Intent -> Authorization/Approval -> GEO -> O45 ExecutionService -> ToolRegistry -> Handler -> Outcome -> Persistence/Audit -> Response`

Do not introduce a parallel canonical path without explicit architectural approval.

## Agent Roles
- Architect / Acceptance Gate: defines scope, contract ownership, evidence requirements, and acceptance.
- Claude: primary implementation engineer for deep multi-file changes and debugging.
- Gemini / Google AI Studio: independent adversarial reviewer and second implementation engineer.
- GitHub Copilot: Git-native coding, branch/PR assistance, focused implementation, and code review.
- Human operator: runs the Windows verification commands and reports actual results.

Agents may suggest changes outside their role, but the acceptance gate decides whether they become part of the canonical system.

## Non-Negotiable Invariants
1. Governance remains authoritative.
2. Authorization and approval boundaries must not be bypassed.
3. Consequential actions must not auto-execute merely because an intent was submitted.
4. `action != tool_name`: action is the business/risk classification; `tool_name` is the technical registry target.
5. `run_id` is the cross-system correlation key.
6. Preserve identity propagation and `requested_by` semantics.
7. Preserve boundary-level security guarantees; do not infer application outcomes from security-boundary fields.
8. Do not alter canonical contracts for convenience.
9. Prefer narrow, reversible, additive patches.
10. Every behavioral change requires focused regression tests.
11. No secrets, tokens, credentials, private keys, runtime databases, logs, generated caches, or binaries in Git.
12. Never claim PASS, VERIFIED, or production-ready without actual execution evidence.
13. Never weaken a test merely to make it pass.
14. Do not introduce PowerShell in Windows instructions; use CMD.
15. Do not use `echo` wrappers in Windows instructions.

## Change Workflow
1. State the exact objective and affected contract.
2. Inspect the actual code before proposing a patch.
3. Identify the owning module/file.
4. Implement the smallest safe change.
5. Add or update focused tests.
6. Run deterministic verification.
7. Capture exact evidence.
8. Review the diff before merge.
9. Keep `main` protected by review; work on branches for implementation.

## Stop Conditions
Stop and request architectural review when:
- a proposed change bypasses Governance, Authorization, or Approval;
- a new execution route competes with the canonical path;
- a contract owner is unclear;
- a change requires secrets or credentials to be copied into source control;
- a failure suggests the existing architecture is inconsistent rather than locally defective.

## Evidence Standard
A result is:
- PASS only when the named test/gate actually ran and returned success.
- SKIPPED only when the output explicitly says skipped.
- NOT_CONFIGURED when required provider configuration is absent.
- VERIFIED only after the human operator confirms the observed result.
