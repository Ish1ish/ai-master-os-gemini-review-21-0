# AI Master OS — O38 Production Security Gate

Release: `O38-v1.4.0`

## Automated verification
- Combined unit/regression/security: **49/49 PASS**
- `PYTHONWARNINGS=error::ResourceWarning`: **PASS**
- `compileall`: **PASS**
- Production identity secret fail-closed: **PASS**
- Signed bearer positive/negative HTTP boundary tests: **PASS**
- Production provider configuration fail-fast: **PASS**
- SQLite backup/restore integrity drill: **PASS**

## Production controls added
- SQLite backup/verify helpers explicitly close connections to avoid Windows file-handle leaks during temporary-directory cleanup.
- The Windows go-live wrapper fails closed on any unexpected non-zero gate exit and never prints READY after a gate error.
- Sensitive HTTP routes are denied without signed bearer credentials when production mode is enabled.
- `AI_OS_IDENTITY_SIGNING_SECRET` is mandatory in production; no development fallback is used in production mode.
- Production service examples bind the application API to loopback.
- TLS termination topology is provided through the Nginx example.
- Production mode selects externally configured live model/search providers instead of deterministic fake providers.
- SQLite backup and restore verification scripts are included.
- Secrets remain external to the release archive.
- An explicit `staging_provider_smoke.py` is included; it runs real provider requests only when the operator injects the target credentials.

## External go-live checks
The following require the actual target environment and cannot be truthfully marked complete inside a portable package:
1. real-provider staging smoke with target credentials;
2. firewall/public-port verification;
3. certificate issuance/rotation drill;
4. backup retention and restore drill against production persistent stores;
5. rollback execution in the target environment.

## Decision
**OFFLINE-HARDENED / SINGLE REAL-RUN VALIDATION PENDING**. The portable package is not a substitute for target-infrastructure evidence.
