from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterable, Optional


RISK_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
TERMINAL_DECISIONS = {"AUTO_ALLOW", "REVIEW", "BLOCK"}


class CounterfactualPreflight:
    """Pure, side-effect-free simulation of a governed execution plan.

    This is deliberately *not* an execution path. It predicts the control-plane
    posture before durable execution records, approvals, or external effects are
    created. The output is deterministic for the same inputs.
    """

    def __init__(self, governance, receipts=None, registry=None):
        self.governance = governance
        self.receipts = receipts
        self.registry = registry

    @staticmethod
    def _canonical_action(item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": str(item.get("action") or ""),
            "tool_name": str(item.get("tool_name") or ""),
            "payload": item.get("payload") or {},
            "idempotency_key": str(item.get("idempotency_key") or ""),
        }

    @staticmethod
    def _plan_hash(actions: Iterable[Dict[str, Any]]) -> str:
        raw = json.dumps(list(actions), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _empty_result(project_id: str, requested_by: str, reason: Optional[str] = None) -> Dict[str, Any]:
        result = {
            "status": "BLOCK" if reason else "PASS",
            "project_id": project_id,
            "requested_by": requested_by,
            "decision": "BLOCK" if reason else "AUTO_ALLOW",
            "risk": "HIGH" if reason else "LOW",
            "actions": [],
            "summary": {
                "action_count": 0,
                "auto_allow": 0,
                "review": 0,
                "block": 1 if reason else 0,
                "estimated_approvals": 0,
            },
        }
        if reason:
            result["reason"] = reason
        return result

    def simulate(
        self,
        *,
        project_id: str,
        requested_by: str,
        actions: list[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Return deterministic predicted governance/execution posture."""
        project_id = str(project_id or "").strip()
        requested_by = str(requested_by or "").strip()
        context = dict(context or {})
        if not project_id:
            return self._empty_result(project_id, requested_by, "project_id_required")
        if not requested_by:
            return self._empty_result(project_id, requested_by, "requested_by_required")
        if not isinstance(actions, list) or not actions:
            return self._empty_result(project_id, requested_by, "actions_required")

        canonical = []
        seen_keys = set()
        duplicate_keys = set()
        for index, raw in enumerate(actions):
            if not isinstance(raw, dict):
                return self._empty_result(project_id, requested_by, f"action_{index}_must_be_object")
            item = self._canonical_action(raw)
            for field in ("action", "tool_name", "idempotency_key"):
                if not item[field]:
                    return self._empty_result(project_id, requested_by, f"action_{index}_{field}_required")
            if not isinstance(item["payload"], dict):
                return self._empty_result(project_id, requested_by, f"action_{index}_payload_must_be_object")
            if item["idempotency_key"] in seen_keys:
                duplicate_keys.add(item["idempotency_key"])
            seen_keys.add(item["idempotency_key"])
            canonical.append(item)

        results = []
        highest_risk = "LOW"
        auto_allow = review = blocked = approvals = 0
        existing_receipts = 0
        tool_errors = 0
        reasons = []

        for index, item in enumerate(canonical):
            action_context = dict(context)
            action_context.update(item["payload"].get("context") or {}) if isinstance(item["payload"], dict) else None

            if item["idempotency_key"] in duplicate_keys:
                predicted = {
                    "decision": "BLOCK",
                    "risk": "HIGH",
                    "reason_code": "duplicate_plan_idempotency_key",
                    "approval_required": False,
                    "execution_allowed": False,
                }
            else:
                try:
                    predicted = self.governance.classify(item["action"], action_context)
                except Exception as exc:  # deterministic fail-closed boundary
                    predicted = {
                        "decision": "BLOCK",
                        "risk": "HIGH",
                        "reason_code": "governance_preflight_error",
                        "approval_required": False,
                        "execution_allowed": False,
                        "error_type": type(exc).__name__,
                    }

            risk = str(predicted.get("risk") or "HIGH").upper()
            if risk not in RISK_ORDER:
                risk = "HIGH"
            if RISK_ORDER[risk] > RISK_ORDER[highest_risk]:
                highest_risk = risk

            decision = str(predicted.get("decision") or "BLOCK").upper()
            if decision not in TERMINAL_DECISIONS:
                decision = "BLOCK"

            existing = None
            if self.receipts is not None:
                try:
                    existing = self.receipts.by_idempotency(item["idempotency_key"])
                except Exception:
                    existing = None
            if existing:
                existing_receipts += 1

            if self.registry is not None:
                try:
                    self.registry.resolve(item["tool_name"])
                except (KeyError, PermissionError):
                    tool_errors += 1
                    decision = "BLOCK"
                    risk = "HIGH"
                    predicted = dict(predicted)
                    predicted["reason_code"] = "tool_unavailable"

            if decision == "AUTO_ALLOW":
                auto_allow += 1
            elif decision == "REVIEW":
                review += 1
                approvals += 1
            else:
                blocked += 1

            result = {
                "index": index,
                "action": item["action"],
                "tool_name": item["tool_name"],
                "idempotency_key": item["idempotency_key"],
                "predicted_decision": decision,
                "predicted_risk": risk,
                "approval_required": bool(predicted.get("approval_required")) or decision == "REVIEW",
                "existing_execution": bool(existing),
                "reason_code": predicted.get("reason_code"),
                "execution_allowed": bool(predicted.get("execution_allowed")) and decision != "BLOCK",
            }
            if predicted.get("error_type"):
                result["error_type"] = predicted["error_type"]
            results.append(result)
            if result["reason_code"]:
                reasons.append(result["reason_code"])

        if blocked:
            overall = "BLOCK"
            status = "BLOCK"
        elif review:
            overall = "REVIEW"
            status = "REVIEW"
        else:
            overall = "AUTO_ALLOW"
            status = "PASS"

        plan_hash = self._plan_hash(canonical)
        return {
            "status": status,
            "project_id": project_id,
            "requested_by": requested_by,
            "decision": overall,
            "risk": highest_risk,
            "plan_hash": plan_hash,
            "side_effects": "NONE",
            "actions": results,
            "summary": {
                "action_count": len(results),
                "auto_allow": auto_allow,
                "review": review,
                "block": blocked,
                "estimated_approvals": approvals,
                "existing_execution_receipts": existing_receipts,
                "tool_resolution_errors": tool_errors,
                "unique_reason_codes": sorted(set(reasons)),
            },
        }
