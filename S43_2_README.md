# O39-S43.2 Security Adversarial Gate Wiring Fix

Fixes the S43 gate's false-negative contract checks.

- Detects the actual O36 issue/verify contract (`issue_token` + `_authenticate_token` + signature rejection) instead of requiring a `verify_token` method.
- Detects tenant security references from the actual adversarial drill and unified tenant/isolation sources.
- Root-level overlay paths are used so extraction directly replaces the current gate.
- No production actions, external network calls, or memory writes.
