---
applyTo: "tests/**,src/core/tests/**,**/*_test.py"
---

# Test Rules

Tests are executable contracts.

For each behavior change:
1. Add a focused regression test.
2. Keep assertions aligned with the actual contract shape.
3. Cover both success and blocking/failure behavior where relevant.
4. Verify that forbidden execution paths are not called.
5. Do not weaken assertions just to match a failing implementation.
6. Record exact pass/skip/fail evidence.

A test suite passing does not by itself authorize a claim of production readiness.
