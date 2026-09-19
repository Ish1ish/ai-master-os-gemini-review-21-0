# O45-S53 — Real Provider Closed-Loop Failure Injection & Recovery

Adds a bounded failure-injection/recovery layer around the verified S52 real-provider closed loop.

Checks:
- deterministic transient model/search failure injection
- bounded retry/recovery
- persistent failure fails closed
- S52/S51 two-cycle loop remains intact after recovery
- next decision re-entry remains traceable
- no external action, memory write, or auto-execution

This patch does not replace S52 or change provider credentials.
