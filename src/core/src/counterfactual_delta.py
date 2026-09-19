from __future__ import annotations

from typing import Any, Dict, Iterable

RISK_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}


class CounterfactualDelta:
    """Deterministic comparison of two counterfactual preflight postures.

    This is analysis-only: it compares simulation outputs and never executes,
    approves, rejects, or mutates runtime state.
    """

    @staticmethod
    def _index(actions: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        out = {}
        for item in actions or []:
            key = str(item.get("idempotency_key") or item.get("action") or "")
            if key and key not in out:
                out[key] = item
        return out

    @staticmethod
    def compare(baseline: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(baseline, dict) or not isinstance(candidate, dict):
            return {"status": "BLOCK", "reason": "both_results_required"}
        if baseline.get("side_effects") not in (None, "NONE") or candidate.get("side_effects") not in (None, "NONE"):
            return {"status": "BLOCK", "reason": "delta_requires_side_effect_free_results"}

        b_actions = CounterfactualDelta._index(baseline.get("actions"))
        c_actions = CounterfactualDelta._index(candidate.get("actions"))
        added = [k for k in c_actions if k not in b_actions]
        removed = [k for k in b_actions if k not in c_actions]
        changed = []

        for key in sorted(set(b_actions) & set(c_actions)):
            b = b_actions[key]; c = c_actions[key]
            fields = {}
            for field in ("action", "tool_name", "predicted_decision", "predicted_risk", "approval_required", "execution_allowed", "reason_code"):
                if b.get(field) != c.get(field):
                    fields[field] = {"from": b.get(field), "to": c.get(field)}
            if fields:
                changed.append({"idempotency_key": key, "changes": fields})

        b_summary = baseline.get("summary") or {}
        c_summary = candidate.get("summary") or {}
        b_decision = str(baseline.get("decision") or "BLOCK")
        c_decision = str(candidate.get("decision") or "BLOCK")
        b_risk = str(baseline.get("risk") or "HIGH")
        c_risk = str(candidate.get("risk") or "HIGH")

        risk_delta = RISK_ORDER.get(c_risk, 3) - RISK_ORDER.get(b_risk, 3)
        posture = "UNCHANGED" if b_decision == c_decision and b_risk == c_risk else "CHANGED"

        drivers = []
        if added:
            drivers.append("actions_added")
        if removed:
            drivers.append("actions_removed")
        if changed:
            drivers.append("actions_changed")
        if b_decision != c_decision:
            drivers.append("overall_decision_changed")
        if b_risk != c_risk:
            drivers.append("overall_risk_changed")
        if b_summary.get("estimated_approvals", 0) != c_summary.get("estimated_approvals", 0):
            drivers.append("approval_burden_changed")

        return {
            "status": "PASS",
            "posture": posture,
            "baseline": {"decision": b_decision, "risk": b_risk, "plan_hash": baseline.get("plan_hash")},
            "candidate": {"decision": c_decision, "risk": c_risk, "plan_hash": candidate.get("plan_hash")},
            "risk_delta": risk_delta,
            "decision_changed": b_decision != c_decision,
            "added_actions": sorted(added),
            "removed_actions": sorted(removed),
            "changed_actions": changed,
            "estimated_approvals": {
                "from": b_summary.get("estimated_approvals", 0),
                "to": c_summary.get("estimated_approvals", 0),
            },
            "drivers": drivers,
            "explanation": CounterfactualDelta._explain(b_decision, c_decision, b_risk, c_risk, added, removed, changed),
            "side_effects": "NONE",
        }

    @staticmethod
    def _explain(b_decision, c_decision, b_risk, c_risk, added, removed, changed):
        parts = []
        if b_decision != c_decision:
            parts.append(f"overall decision changed from {b_decision} to {c_decision}")
        if b_risk != c_risk:
            parts.append(f"overall risk changed from {b_risk} to {c_risk}")
        if added:
            parts.append(f"{len(added)} action(s) added")
        if removed:
            parts.append(f"{len(removed)} action(s) removed")
        if changed:
            parts.append(f"{len(changed)} existing action(s) changed posture or metadata")
        return "; ".join(parts) if parts else "no governance-relevant delta detected"
