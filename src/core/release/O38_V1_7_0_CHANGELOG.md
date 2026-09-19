# O38 v1.7.0 — Semantic Contract + Input Normalization Hardening

## Semantic contract fixes
- Preserve a canonical `problem_statement` from Idea Engine into Idea → Strategy and Strategy → Product handoffs.
- Keep Product `core_problem` in problem language rather than offer/feature or vendor language.
- Carry the source signal type so semantic normalization can distinguish pricing/market-gap/competitive/problem signals.
- Keep provenance references attached to the real Market → Ideas and Ideas → Strategy contracts.

## Runtime input fixes
- Normalize string constraints at the service/job boundary so a string is never iterated character-by-character.
- Preserve multiline constraints as separate constraint items.

## Verification
- Full backend unit/regression suite: 58/58 PASS.
- Python compile check: PASS.
- Offline evaluation harness: 10/10 PASS.

## Boundary note
- This release does not introduce live provider calls or external actions.
