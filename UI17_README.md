# UI17 — Real Data Fallback Alignment

Purpose: fix the Executive Experience hydration path after live verification showed the backend ready while the experience surface reported NOT_FOUND.

Changes:
- prefer the already-known last run id when available;
- align run list discovery to the console's established `limit=25` contract;
- preserve backend authority and explicit mutation boundaries.
