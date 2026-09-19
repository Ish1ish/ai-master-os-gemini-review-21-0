# O39 / S33.3 — Token Refresh + Recovery Gate

S33.2 reached the live HTTPS path after restart but was blocked by an expired staging operator token.

S33.3 refreshes the staging operator token through the O36 identity layer before the recovery test, without printing or exposing the token, then repeats:
- clean stop,
- listener-down verification,
- controlled restart,
- listener-up verification,
- live HTTPS authenticated admission.

This is staging evidence only.
