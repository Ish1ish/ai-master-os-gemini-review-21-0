from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional


SCHEMA_VERSION = "O45-v1.0"


def canonical_request(project_id: str, run_id: Optional[str], action: str,
                      tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": str(project_id),
        "run_id": str(run_id or ""),
        "action": str(action),
        "tool_name": str(tool_name),
        "payload": payload or {},
    }


def request_hash(request: Dict[str, Any]) -> str:
    raw = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def sanitize_error(exc: BaseException) -> Dict[str, str]:
    return {
        "type": type(exc).__name__,
        "message": str(exc)[:2000],
    }


class ExecutionPolicy:
    """Second-line execution policy after O44 governance.

    It rejects malformed execution requests and prevents execution when governance
    is not AUTO_ALLOW or a matching human-approved review exists.
    """

    TERMINAL_STATES = {"BLOCKED", "CANCELLED", "SUCCEEDED", "FAILED_TERMINAL"}

    @staticmethod
    def validate_approval(approval: Optional[Dict[str, Any]], *, action: str,
                          run_id: Optional[str], project_id: str,
                          approval_id: Optional[str], request_hash: Optional[str] = None) -> Dict[str, Any]:
        if not approval_id:
            return {"status": "DENY", "reason": "approval_required"}
        if not approval:
            return {"status": "DENY", "reason": "approval_not_found"}
        if approval.get("approval_id") != approval_id:
            return {"status": "DENY", "reason": "approval_identity_mismatch"}
        if approval.get("action") != action:
            return {"status": "DENY", "reason": "approval_action_mismatch"}
        if str(approval.get("run_id") or "") != str(run_id or ""):
            return {"status": "DENY", "reason": "approval_run_mismatch"}
        payload = approval.get("payload") or {}
        if payload.get("project_id") != project_id:
            return {"status": "DENY", "reason": "approval_project_mismatch"}
        if approval.get("status") != "APPROVED":
            return {"status": "DENY", "reason": "approval_not_approved"}
        if request_hash is not None and (approval.get("payload") or {}).get("o45_request_hash") != request_hash:
            return {"status": "DENY", "reason": "approval_request_mismatch"}
        return {"status": "ALLOW"}


class ExecutionService:
    """O45 durable, idempotent, governed tool/action executor."""

    def __init__(self, governance, registry, receipts, *, worker_id="O45-WORKER",
                 lease_seconds=60):
        self.governance = governance
        self.registry = registry
        self.receipts = receipts
        self.worker_id = worker_id
        self.lease_seconds = max(1, int(lease_seconds))

    def _new_request(self, *, project_id, run_id, action, tool_name, payload,
                     idempotency_key, requested_by, context):
        definition = self.registry.resolve(tool_name)
        request = canonical_request(project_id, run_id, action, tool_name, payload)
        digest = request_hash(request)
        existing = self.receipts.by_idempotency(idempotency_key)
        if existing:
            if existing["request_hash"] != digest:
                return None, {
                    "status": "CONFLICT",
                    "reason": "idempotency_key_reused_with_different_request",
                    "execution_id": existing["execution_id"],
                }
            return definition, existing
        governance_context = dict(context or {})
        governance_context["o45_request_hash"] = digest
        governance = self.governance.evaluate(
            project_id, action, context=governance_context, run_id=run_id,
            requested_by=requested_by, create_approval=True,
        )
        if governance["decision"] == "BLOCK":
            state = "BLOCKED"
        elif governance["decision"] == "REVIEW":
            state = "AWAITING_APPROVAL"
        else:
            state = "READY"
        receipt = self.receipts.create(
            idempotency_key=idempotency_key, project_id=project_id, run_id=run_id,
            action=action, tool_name=tool_name, tool_version=definition.version,
            payload=payload or {}, request_hash=digest,
            governance_decision_id=governance.get("decision_id"),
            approval_id=governance.get("approval_id"),
            requested_by=requested_by, state=state,
        )
        receipt["governance"] = governance
        return definition, receipt

    def request(self, *, project_id: str, run_id: Optional[str], action: str,
                tool_name: str, payload: Optional[Dict[str, Any]],
                context: Optional[Dict[str, Any]], idempotency_key: str,
                requested_by: str) -> Dict[str, Any]:
        if not str(project_id).strip():
            return {"status": "BAD_REQUEST", "reason": "project_id_required"}
        if not str(action).strip():
            return {"status": "BAD_REQUEST", "reason": "action_required"}
        if not str(tool_name).strip():
            return {"status": "BAD_REQUEST", "reason": "tool_name_required"}
        if not str(idempotency_key).strip():
            return {"status": "BAD_REQUEST", "reason": "idempotency_key_required"}
        if not str(requested_by).strip():
            return {"status": "BAD_REQUEST", "reason": "requested_by_required"}
        if not isinstance(payload or {}, dict):
            return {"status": "BAD_REQUEST", "reason": "payload_must_be_object"}

        try:
            definition, item = self._new_request(
                project_id=project_id, run_id=run_id, action=action,
                tool_name=tool_name, payload=payload or {},
                idempotency_key=idempotency_key, requested_by=requested_by,
                context=context or {},
            )
        except KeyError as exc:
            return {"status": "BLOCK", "reason": str(exc).strip("'")}
        except PermissionError as exc:
            return {"status": "BLOCK", "reason": str(exc)}

        if item is None:
            return item
        if item.get("status") == "CONFLICT":
            return item
        if item.get("execution_id"):
            # Existing idempotent receipt.
            return {"status": "ACCEPTED", "execution": item}

        # Defensive; create() returns a receipt.
        return {"status": "ACCEPTED", "execution": item, "tool_version": definition.version}

    def approve_and_ready(self, execution_id: str) -> Dict[str, Any]:
        item = self.receipts.get(execution_id)
        if not item:
            return {"status": "NOT_FOUND", "execution_id": execution_id}
        if item["state"] != "AWAITING_APPROVAL":
            return {"status": "CONFLICT", "state": item["state"], "execution_id": execution_id}
        approval = self.governance.approvals.get(item.get("approval_id"))
        verdict = ExecutionPolicy.validate_approval(
            approval, action=item["action"], run_id=item["run_id"],
            project_id=item["project_id"], approval_id=item.get("approval_id"),
            request_hash=item["request_hash"],
        )
        if verdict["status"] != "ALLOW":
            return {"status": "BLOCKED", "reason": verdict["reason"], "execution_id": execution_id}
        return self.receipts.mark_ready(execution_id)

    def cancel(self, execution_id: str) -> Dict[str, Any]:
        return self.receipts.cancel(execution_id)

    def recover_expired(self, now_epoch=None) -> list[Dict[str, Any]]:
        return self.receipts.recover_expired(now_epoch=now_epoch)

    def retry(self, execution_id: str) -> Dict[str, Any]:
        return self.receipts.retry(execution_id)

    def events(self, execution_id: str) -> list[Dict[str, Any]]:
        return self.receipts.events(execution_id)

    def execute_once(self, execution_id: str, *, authz=None,
                     principal: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        item = self.receipts.get(execution_id)
        if not item:
            return {"status": "NOT_FOUND", "execution_id": execution_id}

        if principal is not None and authz is not None:
            gate = authz.authorize(principal, "job:execute")
            if gate["status"] != "ALLOW":
                return {"status": "DENY", "reason": gate.get("reason", gate["status"])}

        if item["state"] == "AWAITING_APPROVAL":
            return {"status": "PENDING", "reason": "approval_required",
                    "execution": item}
        if item["state"] == "BLOCKED":
            return {"status": "BLOCKED", "reason": "governance_blocked",
                    "execution": item}
        if item["state"] in {"SUCCEEDED", "FAILED_TERMINAL", "CANCELLED"}:
            return {"status": "IDEMPOTENT_REPLAY", "execution": item}
        if item["state"] == "RECOVERY_REQUIRED":
            return {"status": "RECOVERY_REQUIRED", "execution": item}

        claimed = self.receipts.claim(
            execution_id, self.worker_id, lease_seconds=self.lease_seconds
        )
        if not claimed:
            latest = self.receipts.get(execution_id)
            return {"status": "IN_PROGRESS_OR_NOT_READY", "execution": latest}

        # Re-resolve tool after claiming: disabling a tool blocks execution before
        # any handler is invoked.
        try:
            definition = self.registry.resolve(claimed["tool_name"])
        except (KeyError, PermissionError) as exc:
            updated = self.receipts.update_state(
                execution_id, "FAILED_TERMINAL",
                error={"code": "tool_unavailable", "message": str(exc)},
            )
            return {"status": "FAILED", "execution": updated}

        try:
            # A tool receives only the canonical payload, not governance internals.
            result = definition.handler(dict(claimed["payload"]))
        except Exception as exc:
            state = "FAILED_RETRYABLE" if definition.retry_safe else "RECOVERY_REQUIRED"
            error = sanitize_error(exc)
            error["code"] = "tool_failure" if definition.retry_safe else "unknown_side_effect_outcome"
            updated = self.receipts.update_state(execution_id, state, error=error)
            return {"status": state, "execution": updated}

        updated = self.receipts.update_state(
            execution_id, "SUCCEEDED", result=result
        )
        return {"status": "SUCCEEDED", "execution": updated}

    def get(self, execution_id: str) -> Dict[str, Any]:
        item = self.receipts.get(execution_id)
        return item or {"status": "NOT_FOUND", "execution_id": execution_id}

    def list(self, project_id=None, run_id=None, states=None, limit=100):
        return {"status": "OK",
                "executions": self.receipts.list(project_id, run_id, states, limit)}

    def close(self):
        self.receipts.close()
