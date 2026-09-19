"""S6 bridge: Outcome -> Feedback -> Learning -> Adaptation.

This is a deterministic Unified Runtime boundary over the authoritative
S5 outcome. It preserves the existing O43/strategy-feedback/strategy-
adaptation semantics without creating a second memory store or strategy engine.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping


class UnifiedLearningAdaptationAdapter:
    # PATCH_02_O45_UNIFIED_BRIDGE_V6
    OUTCOME_TO_SIGNAL = {
        "SUCCESS": ("POSITIVE_STRATEGY_SIGNAL", "MAINTAIN_STRATEGY", "positive_outcome_supports_current_strategy"),
        "FAILURE": ("NEGATIVE_STRATEGY_SIGNAL", "EXPLORE_ALTERNATIVE", "negative_outcome_requires_strategy_reassessment"),
        "BLOCKED": ("INCONCLUSIVE_SIGNAL", "COLLECT_EVIDENCE", "blocked_execution_is_not_strategy_evidence"),
    }

    def run(
        self,
        outcome: Mapping[str, Any],
        *,
        strategy_id: str,
        run_id: str,
        project_id: str,
    ) -> Dict[str, Any]:
        if not isinstance(outcome, Mapping):
            raise TypeError("outcome_must_be_mapping")
        if not strategy_id or not run_id or not project_id:
            raise ValueError("strategy_run_project_identity_required")

        status = str(outcome.get("outcome_status") or "").upper()
        if status == "PENDING":
            learning = {
                "learning_status": "NOT_COMMITTED",
                "lesson": "Execution is not terminal; learning waits for the authoritative execution outcome.",
                "attribution": "EXECUTION_PENDING",
                "evidence_sufficiency": "INSUFFICIENT",
                "source_outcome": status,
            }
            adaptation = {
                "posture": "WAIT_FOR_OUTCOME",
                "recommendation": "WAIT_FOR_OUTCOME",
                "reason": "execution_pending_waiting_for_terminal_outcome",
                "authoritative": True,
                "external_action": False,
                "o43_mutation": False,
            }
            envelope = {
                "status": "ADAPTATION_READY",
                "run_id": run_id,
                "project_id": project_id,
                "strategy_id": strategy_id,
                "source_execution_id": outcome.get("execution_id"),
                "feedback": {
                    "signal": "INCONCLUSIVE_SIGNAL",
                    "route": "WAIT_FOR_OUTCOME",
                    "reason": "execution_pending_waiting_for_terminal_outcome",
                    "attribution": "EXECUTION_PENDING",
                },
                "learning": learning,
                "adaptation": adaptation,
                "memory_write": False,
                "external_action": False,
            }
            envelope["learning_fingerprint"] = hashlib.sha256(
                json.dumps(
                    {
                        "run_id": run_id,
                        "project_id": project_id,
                        "strategy_id": strategy_id,
                        "signal": "INCONCLUSIVE_SIGNAL",
                        "learning": learning,
                        "adaptation": adaptation,
                    },
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest()
            return envelope

        if status not in self.OUTCOME_TO_SIGNAL:
            return {
                "status": "BLOCKED",
                "reason": "unsupported_outcome_status",
                "run_id": run_id,
                "project_id": project_id,
                "strategy_id": strategy_id,
                "feedback": {
                    "signal": "INCONCLUSIVE_SIGNAL",
                    "route": "COLLECT_EVIDENCE",
                    "attribution": "NO_DECISION_GRADE_EVIDENCE",
                },
                "learning": {
                    "learning_status": "NOT_COMMITTED",
                    "lesson": "Unsupported outcome does not become learning.",
                },
                "adaptation": {
                    "posture": "COLLECT_EVIDENCE",
                    "recommendation": "COLLECT_EVIDENCE",
                    "authoritative": True,
                },
                "memory_write": False,
                "external_action": False,
            }

        signal, recommendation, reason = self.OUTCOME_TO_SIGNAL[status]

        if status == "SUCCESS":
            attribution = "DECISION"
            evidence_sufficiency = "OBSERVED_SUCCESS"
            learning_status = "LEARNABLE"
            lesson = "Observed successful execution supports the current strategy; maintain unless stronger contradictory evidence appears."
            adaptation_reason = "positive_feedback_supports_strategy"
        elif status == "FAILURE":
            attribution = "DECISION"
            evidence_sufficiency = "OBSERVED_FAILURE"
            learning_status = "LEARNABLE"
            lesson = "Observed execution failure is strategy feedback only when attributable to the selected strategy rather than the execution environment."
            adaptation_reason = "negative_feedback_routes_to_alternative_hypothesis"
        else:
            attribution = "EXECUTION_BLOCK"
            evidence_sufficiency = "INSUFFICIENT"
            learning_status = "NOT_DECISION_DRIVING"
            lesson = "A blocked execution is not sufficient evidence to learn that the strategy failed."
            adaptation_reason = "blocked_execution_requires_more_evidence"

        learning = {
            "learning_status": learning_status,
            "lesson": lesson,
            "attribution": attribution,
            "evidence_sufficiency": evidence_sufficiency,
            "source_outcome": status,
        }

        adaptation = {
            "posture": recommendation,
            "recommendation": recommendation,
            "reason": adaptation_reason,
            "authoritative": True,
            "external_action": False,
            "o43_mutation": False,
        }

        envelope = {
            "status": "ADAPTATION_READY",
            "run_id": run_id,
            "project_id": project_id,
            "strategy_id": strategy_id,
            "source_execution_id": outcome.get("execution_id"),
            "feedback": {
                "signal": signal,
                "route": recommendation,
                "reason": reason,
                "attribution": attribution,
            },
            "learning": learning,
            "adaptation": adaptation,
            "memory_write": False,
            "external_action": False,
        }
        envelope["learning_fingerprint"] = hashlib.sha256(
            json.dumps(
                {
                    "run_id": run_id,
                    "project_id": project_id,
                    "strategy_id": strategy_id,
                    "signal": signal,
                    "learning": learning,
                    "adaptation": adaptation,
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        return envelope
