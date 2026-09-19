S25 — Package Import Alignment Fix

Root cause: the workspace contains a top-level `src` namespace for strategy modules and a nested `src\core\src` package for O26/O42/O38 modules. Adding both roots to PYTHONPATH caused Python to resolve `src` to `src\core\src`, hiding `src.strategy_*`.

Fix:
- canonicalize Unified Runtime imports to `core.src.unified_decision_intelligence` and `core.src.evidence_loop`.
- no changes to S19/S20/S21/O36 security behavior.
- add focused regression coverage for coexistence of strategy and core namespaces.
