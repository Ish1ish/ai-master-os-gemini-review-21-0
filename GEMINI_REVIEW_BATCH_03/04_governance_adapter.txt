"""S4 Governance boundary for the Unified Runtime.

Consumes the canonical S3 EVALUATION result and deterministically maps it to a
governance posture. This layer does not execute external actions and does not
mutate governance state.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping


class UnifiedGovernanceAdapter:
    DECISIONS = {"GO", "REFINE", "NO-GO", "INCONCLUSIVE"}

    def evaluate(self, evaluation: Mapping[str, Any], *, run_id: str, project_id: str) -> Dict[str, Any]:
        if not isinstance(evaluation, Mapping):
            raise TypeError("evaluation_must_be_mapping")
        if not run_id or not project_id:
            raise ValueError("run_id_and_project_id_are_required")

        decision = str(evaluation.get("decision") or "").upper()
        if decision not in self.DECISIONS:
            return {
                "status": "BLOCKED",
                "decision": None,
                "posture": "BLOCK",
                "reason": "invalid_or_missing_evaluation_decision",
                "run_id": run_id,
                "project_id": project_id,
                "approval_required": False,
                "external_action_allowed": False,
                "external_action_executed": False,
                "governance_mutation": False,
            }

        completed = bool(evaluation.get("completed"))
        confidence = evaluation.get("confidence")
        governance = {
            "status": "GOVERNED",
            "decision": decision,
            "run_id": run_id,
            "project_id": project_id,
            "confidence": confidence,
            "approval_required": False,
            "approval_status": "NOT_REQUIRED",
            "external_action_allowed": False,
            "external_action_executed": False,
            "governance_mutation": False,
            "reason": "",
            "posture": "",
        }

        if not completed:
            governance.update(
                status="BLOCKED",
                posture="BLOCK",
                reason="evaluation_not_completed",
            )
            return governance

        if decision == "GO":
            governance.update(
                posture="PROCEED_TO_EXECUTION_GATE",
                reason="evaluation_go_with_governance_gate",
            )
        elif decision == "REFINE":
            governance.update(
                posture="REFINE_BEFORE_EXECUTION",
                reason="evaluation_requires_refinement",
            )
        elif decision == "NO-GO":
            governance.update(
                posture="DO_NOT_PROCEED",
                reason="evaluation_no_go",
            )
        else:
            governance.update(
                posture="HOLD_FOR_MORE_EVIDENCE",
                reason="evaluation_inconclusive",
            )

        return governance
