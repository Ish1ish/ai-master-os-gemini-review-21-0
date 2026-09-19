# O39 Operations Runbook

## Start
1. Load protected production environment variables.
2. Run `python scripts/init_databases.py` if the databases are not initialized.
3. Run `python scripts/startup_check.py`.
4. Start the API with loopback binding.
5. Start the console separately.

## Verify
Run `scripts\windows_ops_snapshot.cmd` and confirm:
- release matches the manifest,
- required environment is READY,
- SQLite integrity checks are `ok` for existing databases,
- local `/health` is `OK`,
- local `/readiness` is `HEALTHY`.

## Incident response
- FAILED run: inspect the run payload and audit trail before retrying.
- QUEUED/RUNNING stuck job: use the existing operator recovery/retry path; do not edit SQLite manually.
- Provider outage: keep the runtime in a governed failed/degraded state; do not bypass provider boundaries.
- Approval pending: no external consequential action should be released.

## Rollback
Stop the runtime, restore the previous package and compatible database snapshot, then rerun the offline verification and operator snapshot before resuming traffic.
