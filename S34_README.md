# O39 / S34 — Production Identity Secret Contract Hardening

Goal:
Prove the O36 identity layer fails closed when production mode has no identity signing secret, while accepting a supplied production signing secret.

Checks:
- production mode + missing signing secret => initialization MUST fail
- production mode + supplied signing secret => initialization MUST succeed
- staging mode + supplied signing secret => initialization MUST succeed

No real secret is read, printed, stored, or modified by this gate.
The positive secret is a test-only sentinel held only in the child process environment.

This gate validates the identity contract already present in the current O36 implementation and creates explicit operational evidence for the production requirement.

This does not grant internet-facing production approval.
