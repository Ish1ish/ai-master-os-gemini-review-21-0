from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterable, List, Optional


SCHEMA_VERSION = "ADC-v1.0"

POSTURES = {
    "COLD_START",
    "NORMAL",
    "ELEVATED_CAUTION",
    "INVESTIGATE_EXECUTION",
    "COLLECT_MORE_EVIDENCE",
}

ADVISORY_DECISIONS = {"RECOMMEND", "REFINE", "HOLD", "BLOCK"}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def deterministic_id(prefix: str, value: Any, length: int = 24) -> str:
    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()[:length]
    return f"{prefix}-{digest.upper()}"


class AdaptiveDecisionContext:
    """Bounded advisory bridge from v1.6 patterns into a new decision context.

    It can increase caution or request refinement/evidence collection, but it
    never lowers governance, executes actions, changes authorization, or writes
    directly into O43 memory.
    """

    def build(
        self,
        *,
        project_id: str,
        analysis: Optional[Dict[str, Any]],
        candidate_decision: str,
        governance_required: bool = True,
        evidence_sufficient: bool = True,
    ) -> Dict[str, Any]:
        project_id = str(project_id or "").strip()
        if not project_id:
            raise ValueError("project_id_required")

        candidate_decision = str(candidate_decision or "HOLD").upper()
        if candidate_decision not in ADVISORY_DECISIONS:
            raise ValueError("invalid_candidate_decision")

        if analysis is None:
            status = "COLD_START"
            posture = "COLD_START"
            reasons = ["NO_PRIOR_OUTCOME_ANALYSIS"]
        else:
            if str(analysis.get("project_id") or "") != project_id:
                raise ValueError("project_mismatch")
            if not evidence_sufficient:
                status = "INSUFFICIENT_EVIDENCE"
                posture = "COLLECT_MORE_EVIDENCE"
                reasons = ["CURRENT_DECISION_EVIDENCE_INSUFFICIENT"]
            else:
                status, posture, reasons = self._derive_posture(analysis)

        advisory_decision = self._derive_advisory_decision(
            candidate_decision=candidate_decision,
            posture=posture,
            evidence_sufficient=evidence_sufficient,
        )

        payload_key = {
            "project_id": project_id,
            "analysis_id": None if analysis is None else analysis.get("analysis_id"),
            "candidate_decision": candidate_decision,
            "governance_required": bool(governance_required),
            "evidence_sufficient": bool(evidence_sufficient),
            "posture": posture,
            "advisory_decision": advisory_decision,
        }

        return {
            "schema_version": SCHEMA_VERSION,
            "context_id": deterministic_id("ADC", payload_key),
            "project_id": project_id,
            "analysis_id": None if analysis is None else analysis.get("analysis_id"),
            "status": status,
            "candidate_decision": candidate_decision,
            "advisory_decision": advisory_decision,
            "advisory_posture": posture,
            "reasons": reasons,
            "governance_required": bool(governance_required),
            "governance_authority": "POLICY_AND_GOVERNANCE_REMAIN_AUTHORITATIVE",
            "evidence_sufficient": bool(evidence_sufficient),
            "external_action_executed": False,
            "o43_memory_mutated": False,
            "adaptation_applied": advisory_decision != candidate_decision,
            "boundary": (
                "Adaptive context may increase caution or request refinement/evidence; "
                "it cannot lower, bypass, or override governance and never executes actions."
            ),
        }

    @staticmethod
    def _derive_posture(analysis: Dict[str, Any]) -> tuple[str, str, List[str]]:
        status = str(analysis.get("analysis_status") or "INSUFFICIENT_SAMPLE").upper()
        route = str(analysis.get("advisory_route") or "COLLECT_MORE_EVIDENCE").upper()
        sample_size = int(analysis.get("sample_size") or 0)
        confidence = str(analysis.get("confidence") or "unknown").lower()
        findings = {str(x).upper() for x in (analysis.get("findings") or [])}

        if status != "ANALYZED" or sample_size < 3:
            return "INSUFFICIENT_EVIDENCE", "COLLECT_MORE_EVIDENCE", [
                "OUTCOME_ANALYSIS_NOT_SUFFICIENT_FOR_ADAPTATION"
            ]

        if route == "COLLECT_MORE_EVIDENCE":
            return "INSUFFICIENT_EVIDENCE", "COLLECT_MORE_EVIDENCE", [
                "HISTORICAL_EVIDENCE_COVERAGE_INSUFFICIENT"
            ]

        if route == "INVESTIGATE_EXECUTION" or "REPEATED_EXECUTION_MISMATCH" in findings:
            return "ADVISORY_READY", "INVESTIGATE_EXECUTION", [
                "REPEATED_EXECUTION_MISMATCH"
            ]

        if route == "REFINE_DECISION" or "REPEATED_DECISION_MISSES" in findings:
            return "ADVISORY_READY", "ELEVATED_CAUTION", [
                "REPEATED_DECISION_MISSES"
            ]

        if "EVIDENCE_COVERAGE_WEAK" in findings or confidence == "unknown":
            return "ADVISORY_READY", "COLLECT_MORE_EVIDENCE", [
                "EVIDENCE_COVERAGE_WEAK"
            ]

        return "ADVISORY_READY", "NORMAL", ["NO_ADAPTIVE_CAUTION_REQUIRED"]

    @staticmethod
    def _derive_advisory_decision(
        *,
        candidate_decision: str,
        posture: str,
        evidence_sufficient: bool,
    ) -> str:
        if not evidence_sufficient:
            return "REFINE" if candidate_decision == "RECOMMEND" else candidate_decision

        if candidate_decision in {"BLOCK", "HOLD"}:
            return candidate_decision

        if posture in {"COLLECT_MORE_EVIDENCE", "ELEVATED_CAUTION"}:
            return "REFINE" if candidate_decision == "RECOMMEND" else candidate_decision

        if posture == "INVESTIGATE_EXECUTION":
            return "REFINE" if candidate_decision == "RECOMMEND" else candidate_decision

        return candidate_decision
