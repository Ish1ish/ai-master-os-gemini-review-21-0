# O39-S41 — Crash / Restart / Interrupted-Run Recovery

Purpose: harden runtime lifecycle after S40 state recovery by proving that an interrupted run can be detected after worker loss, reconciled after restart, safely re-queued, resumed exactly once per active lease, and brought to a terminal state without duplicate active execution.

The gate is dependency-free and uses a temporary in-memory recovery model for the controlled drill. It also checks that the current workspace exposes ApplicationService execution and existing worker/recovery implementation markers.

User verification:
```cmd
cd /d "C:\Users\PC\Desktop\AI Master OS\07_WORKSPACE\21.0_Unified_End_to_End_User_Journey"
tar -xf "C:\Users\PC\Desktop\AI Master OS\03_RELEASES\21.0_O39_S41_Crash_Restart_Interrupted_Run_Recovery_patch.zip" -C "."
set "PYTHONPATH=%CD%\src"
python tests\test_s41_crash_recovery.py
python scripts\s41_crash_recovery_gate.py
```

Expected:
- `S41_TARGETED_TESTS_PASS 6/6`
- `S41_CRASH_RECOVERY_PASS`

This gate does not authorize internet-facing production and does not execute external actions or automatic memory writes.
