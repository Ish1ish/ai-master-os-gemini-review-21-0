# O37 Release Candidate Checklist

- [x] O37 version manifest
- [x] Tenant/project storage with tenant foreign key
- [x] Fail-closed cross-tenant isolation
- [x] Explicit global-admin cross-tenant scope
- [x] Project ownership checks
- [x] Durable per-tenant quota accounting
- [x] Concurrent quota bound regression
- [x] Lifecycle / idempotent close
- [x] Windows verification script
- [x] No real credentials bundled

Release blocker conditions:
- cross-tenant access can bypass tenant boundary without explicit global scope
- quota accounting is not tenant-scoped or can exceed configured maximum
- lifecycle emits ResourceWarning under verification
- cumulative smoke fails
- compileall fails
- stale release metadata
