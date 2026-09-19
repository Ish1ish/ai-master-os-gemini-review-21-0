# AI Master OS O37 Production Candidate Runbook

## 1. Prepare
Use Python 3.10+.

Copy `config/.env.example` to a secure environment configuration and populate live provider settings only in the deployment environment. Never commit real credentials.

## 2. Initialize
Run:
```bash
python scripts/init_databases.py
```

## 3. Startup checks
Run:
```bash
python scripts/startup_check.py
```

A `PASS` means the package structure and Python version are valid. `production_env: NOT_CONFIGURED` is expected for local testing.

## 4. Build manifest
Run:
```bash
python scripts/build_manifest.py
```

## 5. Run release evaluation
Run:
```bash
python run_evaluation.py
```

The O37 isolation/release gate must pass. O29 remains a prerequisite regression gate.

## 6. CLI
The packaged service can be invoked through:
```bash
python -m src.cli health
python -m src.cli readiness
python -m src.cli submit --project-id P1 --request "Find a lean AI business opportunity"
```

## 7. Operator notes
- Do not auto-approve consequential external actions.
- Review pending approvals before any public publishing or spending.
- Keep database backups and retention policies outside this package.
- Do not store secrets in source, SQLite payloads, or audit records.

## 8. Rollback
Because this is an RC package, preserve the previous known-good package and databases before upgrading. Roll back by restoring the prior package plus compatible persistent data snapshot.
