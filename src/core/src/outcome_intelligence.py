from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional, Sequence


SCHEMA_VERSION = "OIL-v1.0"

TARGET_STATUSES = {"MET", "PARTIAL", "MISSED", "UNKNOWN"}
OUTCOME_QUALITIES = {
    "FULL_SUCCESS",
    "PARTIAL_SUCCESS",
    "MISSED_TARGET",
    "FAILED",
    "INCONCLUSIVE",
}
ATTRIBUTIONS = {
    "DECISION",
    "EXECUTION",
    "ROUTING",
    "TOOL",
    "GOVERNANCE",
    "INSUFFICIENT_EVIDENCE",
}
LEARNING_SIGNALS = {
    "POSITIVE_CALIBRATION",
    "REFINE",
    "NEGATIVE_SIGNAL",
    "DO_NOT_LEARN",
}


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


class OutcomeIntelligence:
    """Deterministic outcome assessment.

    This layer only interprets already-recorded observability evidence.
    It does not execute tools, change policy, approve actions, or mutate
    the existing O43 learning memory.
    """

    def assess(
        self,
        *,
        trace: Dict[str, Any],
        target_status: str,
        evidence_refs: Optional[Sequence[str]] = None,
        confidence: str = "medium",
        attribution_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not isinstance(trace, dict) or not trace.get("trace_id"):
            raise ValueError("trace_required")

        target_status = str(target_status or "").upper()
        if target_status not in TARGET_STATUSES:
            raise ValueError("invalid_target_status")

        confidence = str(confidence or "").lower()
        if confidence not in {"low", "medium", "high"}:
            raise ValueError("invalid_confidence")

        refs = [
            str(value)
            for value in (evidence_refs or [])
            if str(value).strip()
        ]

        decision_status = str(trace.get("decision_status") or "").upper()
        execution_state = str(trace.get("execution_state") or "").upper()
        outcome_status = str(trace.get("outcome_status") or "").upper()
        outcome_success = self._outcome_success(trace)

        evidence_sufficient = bool(refs) and target_status != "UNKNOWN" and confidence != "low"

        outcome_quality = self._outcome_quality(
            target_status=target_status,
            outcome_success=outcome_success,
            outcome_status=outcome_status,
        )
        attribution = self._attribution(
            target_status=target_status,
            execution_state=execution_state,
            outcome_success=outcome_success,
            attribution_hint=attribution_hint,
        )
        decision_quality = self._decision_quality(
            decision_status=decision_status,
            target_status=target_status,
            outcome_success=outcome_success,
            attribution=attribution,
            evidence_sufficient=evidence_sufficient,
        )
        learning_signal = self._learning_signal(
            outcome_quality=outcome_quality,
            attribution=attribution,
            evidence_sufficient=evidence_sufficient,
        )

        result = {
            "schema_version": SCHEMA_VERSION,
            "assessment_id": "OIA-" + sha256_json({
                "trace_id": trace["trace_id"],
                "target_status": target_status,
                "evidence_refs": refs,
                "confidence": confidence,
                "attribution_hint": attribution_hint,
                "outcome_quality": outcome_quality,
                "decision_quality": decision_quality,
                "attribution": attribution,
                "learning_signal": learning_signal,
            })[:24].upper(),
            "trace_id": trace["trace_id"],
            "project_id": trace.get("project_id"),
            "decision_plan_id": trace.get("decision_plan_id"),
            "intent_id": trace.get("intent_id"),
            "execution_id": trace.get("execution_id"),
            "decision_status": decision_status or None,
            "execution_state": execution_state or None,
            "outcome_status": outcome_status or None,
            "target_status": target_status,
            "outcome_success": outcome_success,
            "outcome_quality": outcome_quality,
            "decision_quality": decision_quality,
            "attribution": attribution,
            "learning_signal": learning_signal,
            "confidence": confidence,
            "evidence_refs": refs,
            "evidence_sufficient": evidence_sufficient,
            "learning_driving": learning_signal != "DO_NOT_LEARN",
            "boundary": (
                "Outcome intelligence is evidence about an observed run, "
                "not proof that future outcomes will match."
            ),
        }
        return result

    @staticmethod
    def _outcome_success(trace: Dict[str, Any]) -> bool:
        outcomes = trace.get("outcomes") or []
        if outcomes:
            return bool(outcomes[-1].get("success"))
        return str(trace.get("outcome_status") or "").upper() == "SUCCEEDED"

    @staticmethod
    def _outcome_quality(
        *,
        target_status: str,
        outcome_success: bool,
        outcome_status: str,
    ) -> str:
        if target_status == "UNKNOWN":
            return "INCONCLUSIVE"
        if not outcome_success or outcome_status in {"FAILED", "ERROR"}:
            return "FAILED"
        if target_status == "MET":
            return "FULL_SUCCESS"
        if target_status == "PARTIAL":
            return "PARTIAL_SUCCESS"
        return "MISSED_TARGET"

    @staticmethod
    def _attribution(
        *,
        target_status: str,
        execution_state: str,
        outcome_success: bool,
        attribution_hint: Optional[str],
    ) -> str:
        if attribution_hint:
            value = str(attribution_hint).upper()
            if value not in ATTRIBUTIONS:
                raise ValueError("invalid_attribution_hint")
            return value

        if execution_state in {"FAILED", "ERROR"} or not outcome_success:
            return "EXECUTION"
        if target_status in {"PARTIAL", "MISSED"}:
            return "DECISION"
        if target_status == "UNKNOWN":
            return "INSUFFICIENT_EVIDENCE"
        return "DECISION"

    @staticmethod
    def _decision_quality(
        *,
        decision_status: str,
        target_status: str,
        outcome_success: bool,
        attribution: str,
        evidence_sufficient: bool,
    ) -> str:
        if not evidence_sufficient or target_status == "UNKNOWN":
            return "INSUFFICIENT_EVIDENCE"
        if attribution == "EXECUTION":
            return "EXECUTION_MISMATCH"
        if outcome_success and target_status == "MET" and decision_status in {
            "RECOMMEND",
            "GO",
            "AUTO_ALLOW",
            "AUTO-ALLOW",
        }:
            return "SOUND_DECISION"
        if target_status in {"PARTIAL", "MISSED"}:
            return "TARGET_MISSED"
        return "UNRESOLVED"

    @staticmethod
    def _learning_signal(
        *,
        outcome_quality: str,
        attribution: str,
        evidence_sufficient: bool,
    ) -> str:
        if not evidence_sufficient:
            return "DO_NOT_LEARN"
        if outcome_quality == "FULL_SUCCESS":
            return "POSITIVE_CALIBRATION"
        if outcome_quality == "PARTIAL_SUCCESS":
            return "REFINE"
        if outcome_quality in {"MISSED_TARGET", "FAILED"}:
            return "NEGATIVE_SIGNAL" if attribution != "EXECUTION" else "REFINE"
        return "DO_NOT_LEARN"
