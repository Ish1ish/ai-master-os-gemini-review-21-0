# UI22 — Full Console Surface Determinism

Fixes a UI-only issue where multiple `.page` surfaces could remain visible during SPA navigation, causing the Recovery reconciliation playbook and legacy surfaces to leak into Golden Experience/Product Acceptance/Experiments and create large blank gaps.

It enforces exactly one visible page from the active sidebar item and trims oversized structured state text in dense journey cards. No API calls or governance mutations are added.
