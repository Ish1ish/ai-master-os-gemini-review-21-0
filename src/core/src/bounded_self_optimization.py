from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterable, Optional

from .decision_uncertainty import DecisionUncertainty


class BoundedSelfOptimizer:
    """Policy-first planner for bounded, reversible self-optimization.

    v0.8 never mutates production behavior directly. It creates deterministic
    proposals, evaluates simulation evidence, derives a governance posture, and
    requires explicit approval before an application outcome can be recorded.
    """

    CHANGE_TYPES = {"PARAMETER", "PROMPT", "ROUTING", "THRESHOLD", "POLICY_ADVISORY"}
    CONSEQUENT_FLAGS = {"external_effect", "financial", "destructive", "sensitive"}
    TERMINAL = {"ROLLED_BACK", "APPLIED", "REJECTED"}

    @staticmethod
    def _canonical(payload: Dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def change_id(cls, project_id: str, proposal: Dict[str, Any]) -> str:
        raw = {"project_id": str(project_id), "proposal": proposal}
        digest = hashlib.sha256(cls._canonical(raw).encode("utf-8")).hexdigest()[:20].upper()
        return f"OPT-{digest}"

    @staticmethod
    def _metric_delta(baseline: Dict[str, Any], simulated: Dict[str, Any]) -> Dict[str, float]:
        keys = sorted(set(baseline) | set(simulated))
        out: Dict[str, float] = {}
        for key in keys:
            left, right = baseline.get(key), simulated.get(key)
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                out[key] = round(float(right) - float(left), 6)
        return out

    @staticmethod
    def _bool(context: Dict[str, Any], key: str) -> bool:
        value = context.get(key)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "y"}

    @classmethod
    def validate_proposal(cls, proposal: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(proposal, dict):
            return {"valid": False, "reasons": ["proposal_must_be_object"]}
        reasons = []
        required = ("component", "change_type", "current_value", "proposed_value", "rationale", "evidence_refs", "rollback_plan")
        for key in required:
            if key not in proposal:
                reasons.append(f"missing_{key}")
        change_type = str(proposal.get("change_type") or "").upper()
        if change_type and change_type not in cls.CHANGE_TYPES:
            reasons.append("unsupported_change_type")
        refs = proposal.get("evidence_refs") or []
        if isinstance(refs, str):
            refs = [refs]
        if not refs:
            reasons.append("evidence_refs_required")
        if not str(proposal.get("rollback_plan") or "").strip():
            reasons.append("rollback_plan_required")
        if proposal.get("apply_mode", "SIMULATION_ONLY") not in {"SIMULATION_ONLY", "GOVERNED_APPLY"}:
            reasons.append("unsupported_apply_mode")
        return {"valid": not reasons, "reasons": reasons}

    @classmethod
    def propose(cls, *, project_id: str, proposal: Dict[str, Any]) -> Dict[str, Any]:
        check = cls.validate_proposal(proposal)
        if not check["valid"]:
            return {"status": "REJECTED", "phase": "PROPOSE", "reasons": check["reasons"]}
        normalized = dict(proposal)
        normalized["change_type"] = str(normalized["change_type"]).upper()
        normalized.setdefault("risk_class", "MEDIUM")
        normalized.setdefault("apply_mode", "SIMULATION_ONLY")
        normalized["change_id"] = normalized.get("change_id") or cls.change_id(project_id, normalized)
        return {
            "status": "PROPOSED",
            "phase": "PROPOSE",
            "project_id": str(project_id),
            "change_id": normalized["change_id"],
            "proposal": normalized,
            "bounds": {
                "simulation_required": True,
                "rollback_required": True,
                "versioned": True,
                "governance_required": True,
                "production_auto_apply": False,
            },
        }

    @classmethod
    def simulate(cls, proposed: Dict[str, Any], *, baseline: Dict[str, Any], simulated: Dict[str, Any], sample_count: int = 0, uncertainty: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if proposed.get("status") != "PROPOSED":
            return {"status": "REJECTED", "phase": "SIMULATE", "reason": "proposal_not_ready"}
        if not isinstance(baseline, dict) or not isinstance(simulated, dict):
            return {"status": "REJECTED", "phase": "SIMULATE", "reason": "metrics_must_be_objects"}
        deltas = cls._metric_delta(baseline, simulated)
        inferred_uncertainty = uncertainty
        if inferred_uncertainty is None:
            inferred_uncertainty = DecisionUncertainty.assess(
                accuracy=None,
                sample_count=sample_count,
                recent_scores=[1.0] if sample_count == 1 else [],
                drift="UNKNOWN",
            )
        return {
            "status": "SIMULATED",
            "phase": "SIMULATE",
            "change_id": proposed["change_id"],
            "baseline_metrics": dict(baseline),
            "simulated_metrics": dict(simulated),
            "metric_delta": deltas,
            "uncertainty": inferred_uncertainty,
            "side_effects": "NONE",
            "production_state_changed": False,
        }

    @classmethod
    def evaluate(cls, proposed: Dict[str, Any], simulation: Dict[str, Any], *, success_metrics: Iterable[str], minimum_improvement: float = 0.0) -> Dict[str, Any]:
        if simulation.get("status") != "SIMULATED":
            return {"status": "INCONCLUSIVE", "decision": "NO-GO", "reason": "simulation_required"}
        keys = [str(k) for k in success_metrics]
        deltas = simulation.get("metric_delta") or {}
        missing = [k for k in keys if k not in deltas]
        if missing:
            return {"status": "INCONCLUSIVE", "decision": "NO-GO", "reason": "success_metrics_missing", "missing": missing}
        passing = {k: float(deltas[k]) >= float(minimum_improvement) for k in keys}
        all_pass = all(passing.values()) if passing else False
        uncertainty = simulation.get("uncertainty") or {}
        if uncertainty.get("uncertainty_band") == "HIGH":
            return {
                "status": "EVALUATED",
                "decision": "REFINE",
                "reason": "high_uncertainty",
                "success_metrics": keys,
                "metric_pass": passing,
                "minimum_improvement": float(minimum_improvement),
            }
        decision = "GO" if all_pass else "NO-GO"
        return {
            "status": "EVALUATED",
            "decision": decision,
            "reason": "all_success_metrics_passed" if all_pass else "success_metric_threshold_not_met",
            "success_metrics": keys,
            "metric_pass": passing,
            "minimum_improvement": float(minimum_improvement),
        }

    @classmethod
    def govern(cls, proposed: Dict[str, Any], evaluation: Dict[str, Any], *, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = dict(context or {})
        proposal = proposed.get("proposal") or {}
        flags = [flag for flag in cls.CONSEQUENT_FLAGS if cls._bool({**proposal, **context}, flag)]
        decision = str(evaluation.get("decision") or "NO-GO")
        risk = str(proposal.get("risk_class") or "MEDIUM").upper()
        refs = proposal.get("evidence_refs") or []
        governance = {
            "status": "REVIEW",
            "decision": "REVIEW",
            "reason": "bounded_optimization_requires_governance_gate",
            "risk_class": risk,
            "consequential_flags": flags,
            "evidence_ref_count": len(refs),
            "evaluation_decision": decision,
            "production_auto_apply": False,
            "governance_authority": "POLICY_AND_GOVERNANCE_REMAIN_AUTHORITATIVE",
        }
        if decision != "GO":
            governance["reason"] = "evaluation_not_GO"
        elif flags:
            governance["reason"] = "consequential_change_requires_explicit_human_approval"
        elif str(proposal.get("apply_mode")) == "SIMULATION_ONLY":
            governance["status"] = "SIMULATION_ONLY"
            governance["decision"] = "SIMULATION_ONLY"
            governance["reason"] = "proposal_is_explicitly_simulation_only"
        return governance

    @classmethod
    def apply(cls, proposed: Dict[str, Any], evaluation: Dict[str, Any], governance: Dict[str, Any], *, approved: bool = False, version: str = "", previous_version: str = "") -> Dict[str, Any]:
        proposal = proposed.get("proposal") or {}
        if not approved:
            return {"status": "REJECTED", "phase": "APPLY", "reason": "explicit_approval_required"}
        if evaluation.get("decision") != "GO":
            return {"status": "REJECTED", "phase": "APPLY", "reason": "evaluation_must_be_GO"}
        if governance.get("decision") not in {"SIMULATION_ONLY", "REVIEW", "AUTO_ALLOW"}:
            return {"status": "REJECTED", "phase": "APPLY", "reason": "invalid_governance_state"}
        if not previous_version or not version:
            return {"status": "REJECTED", "phase": "APPLY", "reason": "version_and_previous_version_required"}
        if str(proposal.get("apply_mode")) == "SIMULATION_ONLY":
            return {"status": "REJECTED", "phase": "APPLY", "reason": "simulation_only_change_cannot_be_applied"}
        return {
            "status": "APPLIED",
            "phase": "APPLY",
            "change_id": proposed["change_id"],
            "version": version,
            "previous_version": previous_version,
            "rollback_available": bool(proposal.get("rollback_plan")),
            "external_action_executed": False,
            "boundary": "v0.8 records an approved bounded state transition; execution of external actions remains outside this component.",
        }

    @classmethod
    def rollback(cls, applied: Dict[str, Any]) -> Dict[str, Any]:
        if applied.get("status") != "APPLIED":
            return {"status": "REJECTED", "phase": "ROLLBACK", "reason": "nothing_applied"}
        return {
            "status": "ROLLED_BACK",
            "phase": "ROLLBACK",
            "change_id": applied.get("change_id"),
            "restored_version": applied.get("previous_version"),
            "rollback_executed": True,
        }


