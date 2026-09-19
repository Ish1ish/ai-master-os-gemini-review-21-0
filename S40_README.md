# O39-S40 — Backup / Restore & State Recovery

This milestone adds a dependency-free backup/restore drill across the durable state domains used by the current runtime foundation.

## Scope
- backup a representative real SQLite state set using the project's JobStore, DurableQueue, ApprovalStore, OperatorStore, CounterfactualDecisionMemory, and ExecutionObservabilityStore schemas
- checkpoint SQLite before file backup
- create a SHA-256 manifest
- simulate destructive loss by deleting the state set
- restore from the manifest-backed backup
- verify file hashes and row-count integrity across jobs, queue, approvals, operator/audit, memory, and execution observability
- verify restore is readable and repeatable
- no production data or credentials are touched by the drill

## Verification
Native Python only; pytest is not required.

```cmd
cd /d "C:\Users\PC\Desktop\AI Master OS\07_WORKSPACE\21.0_Unified_End_to_End_User_Journey"
tar -xf "C:\Users\PC\Desktop\AI Master OS\03_RELEASES\21.0_O39_S40_Backup_Restore_State_Recovery_patch.zip" -C "."
set "PYTHONPATH=%CD%\src"
python tests\test_s40_state_recovery.py
python scripts\s40_state_recovery_gate.py
```

Expected targeted result: `S40_TARGETED_TESTS_PASS 6/6`
Expected gate result: `S40_STATE_RECOVERY_PASS`

The drill runs entirely in isolated temporary directories. It does not publish, spend, message, call external providers, or write automatic memory outside the temporary test fixture.
