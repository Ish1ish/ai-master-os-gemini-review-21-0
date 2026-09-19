# O38 S23 — stdlib `secrets` shadowing fix

## Problem
The workspace contains `src/core/src/secrets.py`. Because `src/core/src` is on `PYTHONPATH`, `import secrets` inside `src/core/src/identity.py` resolves to the project module instead of Python's standard-library `secrets` module. That module has no `token_hex`, so O36 token issuance fails with `AttributeError: module 'secrets' has no attribute 'token_hex'`.

## Fix
Keep the project `secrets.py` unchanged. Remove the ambiguous stdlib import from `identity.py` and generate the token JTI with `os.urandom(16).hex()`, which is cryptographically suitable for an opaque random identifier and does not depend on module lookup for `secrets`.

## Application
From the workspace root:

`python repair_stdlib_secrets_shadowing.py`

The script is idempotent and refuses to modify the file if the expected source text is absent.
