---
applyTo: "src/unified_runtime/**"
---

# Unified Runtime Rules

The unified runtime is a canonical orchestration boundary.

Preserve:
- Security Admission before application dispatch.
- Identity propagation.
- `UnifiedRuntimeEntrypoint` ownership of canonical dispatch.
- `RealUnifiedRuntime` ownership of runtime behavior.
- stage semantics for S1, UDI/Decision, Evaluation, Governance, and Execution Intent.
- boundary-level security fields separately from application outcome fields.

Do not:
- add an alternate execution path;
- infer application execution from boundary guarantee fields;
- auto-execute an O45 intent during a submit/preflight step.
