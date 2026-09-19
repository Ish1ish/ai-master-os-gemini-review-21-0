# 21.0 S2 — O42 Evidence Integration

Adds a narrow Unified Runtime bridge to the existing O42 `ValidationEvidenceLoop`.

Important import boundary:
- O42 files remain under `src\core\src`.
- Runtime imports them directly with `%CD%\src\core\src` on PYTHONPATH.
- The legacy O42 tests import `src.evidence_loop`; for those tests the compatible
  test invocation is from the project root with `%CD%\src\core` available.

Behavior:
- `build_experiment_from_decision_surface()` remains authoritative.
- `ValidationEvidenceLoop.evaluate()` remains authoritative.
- Missing validation experiment fails closed.
- Missing evidence references keep the result INCONCLUSIVE.
- GO / REFINE / NO-GO / INCONCLUSIVE semantics are preserved.
- Unified `run_id` and `project_id` are carried into the experiment.
- No external action is executed by this bridge.
