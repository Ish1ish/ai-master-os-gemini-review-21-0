"""S3 Unified Evaluation boundary over the authoritative O42 result.

O29Evaluator is a system/release evaluator and is intentionally not used here.
This adapter normalizes an already-evaluated O42 result into the Unified Runtime
EVALUATION stage while preserving run/project identity and side-effect boundaries.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping


class UnifiedEvaluationAdapter:
    REQUIRED_KEYS = (
        "decision",
        "confidence",
        "completed",
        "evidence_refs",
        "sample_size",
        "metrics",
        "next_step",
        "decision_boundary",
    )
    ALLOWED_DECISIONS = {"GO", "REFINE", "NO-GO", "INCONCLUSIVE"}

    def normalize(
        self,
        o42_result: Mapping[str, Any],
        *,
        run_id: str,
        project_id: str,
    ) -> Dict[str, Any]:
        if not run_id or not project_id:
            raise ValueError("run_id_and_project_id_are_required")
        if not isinstance(o42_result, Mapping):
            raise TypeError("o42_result_must_be_mapping")

        decision = str(o42_result.get("decision") or "").upper()
        if decision not in self.ALLOWED_DECISIONS:
            raise ValueError("invalid_o42_decision")

        missing = [key for key in self.REQUIRED_KEYS if key not in o42_result]
        if missing:
            raise ValueError(f"o42_result_missing_keys:{','.join(missing)}")

        return {
            "status": "EVALUATED",
            "run_id": run_id,
            "project_id": project_id,
            "decision": decision,
            "confidence": o42_result["confidence"],
            "completed": bool(o42_result["completed"]),
            "checks": list(o42_result.get("checks") or []),
            "met_thresholds": list(o42_result.get("met_thresholds") or []),
            "unmet_thresholds": list(o42_result.get("unmet_thresholds") or []),
            "evidence_refs": [str(x) for x in (o42_result.get("evidence_refs") or [])],
            "sample_size": int(o42_result.get("sample_size") or 0),
            "metrics": dict(o42_result.get("metrics") or {}),
            "learning": str(o42_result.get("learning") or ""),
            "next_step": str(o42_result.get("next_step") or ""),
            "re_run_context": dict(o42_result.get("re_run_context") or {}),
            "decision_boundary": str(o42_result.get("decision_boundary") or ""),
            "external_action": False,
            "external_action_executed": False,
            "governance_mutation": False,
        }
