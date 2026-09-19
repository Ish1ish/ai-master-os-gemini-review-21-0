# O39-S43.1 — Security Adversarial Contract Fix

Fix discovered during user verification of S43.

The S43 adversarial drill itself passed. The failure was a static-gate false negative:
- O36 identity verifies signed bearer tokens through `_authenticate_token` and rejects `invalid_token_signature`; it does not need a method literally named `verify_token`.
- Tenant-isolation evidence is distributed across the unified source tree, so the gate now searches the real `core` and `unified_runtime` Python source instead of only four files.

No network calls, secrets, external actions, or memory writes are introduced.
