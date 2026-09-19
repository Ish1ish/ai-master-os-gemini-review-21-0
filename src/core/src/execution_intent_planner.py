from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional


SCHEMA_VERSION = "EXECUTION-INTENT-v1.0"
CONSEQUENTIAL_ACTIONS = {
    "publish_public_content",
    "send_external_message",
    "spend_ad_budget",
    "change_price",
    "payment_or_refund",
    "delete_or_modify_critical_data",
    "activate_integration",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Any, prefix: str) -> str:
    digest = hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()[:24].upper()
    return f"{prefix}-{digest}"


class ExecutionIntentPlanner:
    # PATCH_02_O45_UNIFIED_BRIDGE_V5
    """Bridge UDI decision plans into governed execution intents.

    Planning-only. It never calls an execution handler, changes governance, or
    submits work. The produced intent is designed to be consumed by O45/O46.
    """

    ALLOWED_DECISION_STATUS = {"RECOMMEND"}

    @classmethod
    def _validate_common(cls, project_id: str, run_id: Optional[str], requested_by: str) -> Optional[str]:
        if not str(project_id).strip():
            return "project_id_required"
        if not str(run_id or "").strip():
            return "run_id_required"
        if not str(requested_by).strip():
            return "requested_by_required"
        return None

    @classmethod
    def build_intent(
        cls,
        *,
        decision_plan: Dict[str, Any],
        action: str,
        payload: Dict[str, Any],
        project_id: str,
        run_id: str,
        requested_by: str,
        tool_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        err = cls._validate_common(project_id, run_id, requested_by)
        if err:
            return {"status": "BLOCKED", "reason": err}
        if not isinstance(decision_plan, dict):
            return {"status": "BLOCKED", "reason": "decision_plan_must_be_object"}
        if str(decision_plan.get("status", "")).upper() not in cls.ALLOWED_DECISION_STATUS:
            return {"status": "BLOCKED", "reason": "decision_plan_not_executable"}
        if not str(decision_plan.get("plan_id", "")).strip():
            return {"status": "BLOCKED", "reason": "decision_plan_id_required"}
        route = decision_plan.get("selected_route")
        if not isinstance(route, dict):
            return {"status": "BLOCKED", "reason": "selected_route_required"}
        provider = str(route.get("provider") or "").strip()
        route_tool_name = str(route.get("tool") or "").strip()
        resolved_tool_name = str(tool_name or route_tool_name).strip()
        if not provider or not route_tool_name or not resolved_tool_name:
            return {"status": "BLOCKED", "reason": "selected_route_identity_required"}
        if not str(action).strip():
            return {"status": "BLOCKED", "reason": "action_required"}
        if not isinstance(payload, dict):
            return {"status": "BLOCKED", "reason": "payload_must_be_object"}

        basis = decision_plan.get("decision_basis") or {}
        governance_required = bool(decision_plan.get("governance_required", True))
        consequential = action in CONSEQUENTIAL_ACTIONS
        requires_review = bool(governance_required or consequential)
        source = {
            "decision_plan_id": str(decision_plan["plan_id"]),
            "project_id": str(project_id),
            "run_id": str(run_id),
            "action": str(action),
            "tool_name": resolved_tool_name,
            "provider": provider,
            "payload": payload,
            "context": dict(context or {}),
            "requested_by": str(requested_by),
        }
        intent_id = _hash(source, "EINT")
        idempotency_key = _hash({"intent_id": intent_id, "schema": SCHEMA_VERSION}, "EKEY")
        execution_request = {
            "project_id": str(project_id),
            "run_id": str(run_id),
            "action": str(action),
            "tool_name": resolved_tool_name,
            "payload": dict(payload),
            "context": {
                **dict(context or {}),
                "decision_plan_id": str(decision_plan["plan_id"]),
                "execution_intent_id": intent_id,
                "provider": provider,
                "decision_basis": dict(basis),
            },
            "idempotency_key": idempotency_key,
            "requested_by": str(requested_by),
        }
        return {
            "status": "PLANNED",
            "intent_id": intent_id,
            "schema_version": SCHEMA_VERSION,
            "decision_plan_id": str(decision_plan["plan_id"]),
            "project_id": str(project_id),
            "run_id": str(run_id),
            "requested_by": str(requested_by),
            "action": str(action),
            "provider": provider,
            "tool_name": resolved_tool_name,
            "payload": dict(payload),
            "governance_required": governance_required,
            "consequential_action": consequential,
            "governance_review_required": requires_review,
            "decision_basis": dict(basis),
            "execution_request": execution_request,
            "execution_started": False,
            "execution_completed": False,
            "recovery_required": False,
            "governance_authority": "POLICY_AND_GOVERNANCE_REMAIN_AUTHORITATIVE",
        }

    @classmethod
    def preflight(cls, intent: Dict[str, Any], *, expected_project_id: Optional[str] = None) -> Dict[str, Any]:
        if not isinstance(intent, dict):
            return {"status": "BLOCKED", "reason": "intent_must_be_object"}
        if intent.get("status") != "PLANNED":
            return {"status": "BLOCKED", "reason": "intent_not_planned"}
        request = intent.get("execution_request")
        if not isinstance(request, dict):
            return {"status": "BLOCKED", "reason": "execution_request_missing"}
        if expected_project_id is not None and request.get("project_id") != expected_project_id:
            return {"status": "BLOCKED", "reason": "project_mismatch"}
        if request.get("idempotency_key") != _hash({"intent_id": intent.get("intent_id"), "schema": SCHEMA_VERSION}, "EKEY"):
            return {"status": "BLOCKED", "reason": "idempotency_key_mismatch"}
        if intent.get("execution_started") or intent.get("execution_completed"):
            return {"status": "BLOCKED", "reason": "intent_already_executed"}
        if intent.get("governance_authority") != "POLICY_AND_GOVERNANCE_REMAIN_AUTHORITATIVE":
            return {"status": "BLOCKED", "reason": "governance_authority_invalid"}
        return {
            "status": "READY_FOR_GOVERNED_SUBMISSION",
            "intent_id": intent["intent_id"],
            "governance_review_required": bool(intent.get("governance_review_required")),
            "external_action_executed": False,
            "recovery_required": False,
        }

    @classmethod
    def record_execution_outcome(cls, intent: Dict[str, Any], execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """Turn an O45 execution result into a bounded post-execution state update."""
        out = dict(intent)
        if not isinstance(execution_result, dict):
            out["recovery_required"] = True
            out["outcome"] = {"status": "RECOVERY_REQUIRED", "reason": "invalid_execution_result"}
            return out
        status = str(execution_result.get("status") or "UNKNOWN")
        out["outcome"] = execution_result
        out["execution_started"] = status not in {"PENDING", "BLOCKED", "NOT_FOUND"}
        out["execution_completed"] = status == "SUCCEEDED"
        out["recovery_required"] = status == "RECOVERY_REQUIRED"
        return out
