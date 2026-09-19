from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .approval_authority import ApprovalAuthority
from .approval_store import ApprovalStore


class GovernanceIntelligence:
    """Deterministic risk/approval classifier for consequential actions.

    O44 is deliberately policy-first. The model does not decide whether an action
    is safe. It only supplies business context; this component derives the final
    governance posture from explicit action metadata, external-effect flags,
    evidence/confidence signals, and approval state.
    """

    ACTIONS = {
        "read_only_inspection": {
            "risk": "LOW", "external_effect": False, "financial": False,
            "destructive": False, "sensitive": False, "reversible": True,
            "required_scope": "governance:evaluate",
        },
        "generate_internal_draft": {
            "risk": "LOW", "external_effect": False, "financial": False,
            "destructive": False, "sensitive": False, "reversible": True,
            "required_scope": "governance:evaluate",
        },
        "write_memory": {
            "risk": "MEDIUM", "external_effect": False, "financial": False,
            "destructive": False, "sensitive": True, "reversible": True,
            "required_scope": "governance:evaluate",
        },
        "schedule_internal_workflow": {
            "risk": "MEDIUM", "external_effect": False, "financial": False,
            "destructive": False, "sensitive": False, "reversible": True,
            "required_scope": "governance:evaluate",
        },
        "publish_public_content": {
            "risk": "HIGH", "external_effect": True, "financial": False,
            "destructive": False, "sensitive": False, "reversible": False,
            "required_scope": "governance:evaluate",
        },
        "send_external_message": {
            "risk": "HIGH", "external_effect": True, "financial": False,
            "destructive": False, "sensitive": True, "reversible": False,
            "required_scope": "governance:evaluate",
        },
        "spend_ad_budget": {
            "risk": "HIGH", "external_effect": True, "financial": True,
            "destructive": False, "sensitive": False, "reversible": False,
            "required_scope": "governance:evaluate",
        },
        "change_price": {
            "risk": "HIGH", "external_effect": True, "financial": True,
            "destructive": False, "sensitive": False, "reversible": True,
            "required_scope": "governance:evaluate",
        },
        "payment_or_refund": {
            "risk": "HIGH", "external_effect": True, "financial": True,
            "destructive": False, "sensitive": True, "reversible": False,
            "required_scope": "governance:evaluate",
        },
        "delete_or_modify_critical_data": {
            "risk": "HIGH", "external_effect": False, "financial": False,
            "destructive": True, "sensitive": True, "reversible": False,
            "required_scope": "governance:evaluate",
        },
        "activate_integration": {
            "risk": "HIGH", "external_effect": True, "financial": False,
            "destructive": False, "sensitive": True, "reversible": True,
            "required_scope": "governance:evaluate",
        },
    }

    RISK_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
    AUTO_ALLOW_MIN_CONFIDENCE = {"high": 1.0, "medium": 0.8, "low": 2.0}

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("AI_OS_GOVERNANCE_DB_PATH") or "./data/governance.sqlite3"
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS governance_decisions(
            decision_id TEXT PRIMARY KEY,
            project_id TEXT,
            run_id TEXT,
            action TEXT,
            decision TEXT,
            risk TEXT,
            confidence TEXT,
            evidence_refs_json TEXT,
            rationale_json TEXT,
            approval_id TEXT,
            created_at TEXT)"""
        )
        self.conn.commit()
        self.approvals = ApprovalStore(os.path.join(os.path.dirname(os.path.abspath(self.db_path)), "approvals.sqlite3"))
        self.authority = ApprovalAuthority()

    @staticmethod
    def _confidence_level(context: Dict[str, Any]) -> str:
        value = context.get("confidence")
        if isinstance(value, (int, float)):
            if value >= 0.8:
                return "high"
            if value >= 0.5:
                return "medium"
            return "low"
        value = str(value or "medium").strip().lower()
        return value if value in {"high", "medium", "low"} else "low"

    @staticmethod
    def _evidence_refs(context: Dict[str, Any]) -> list[str]:
        refs = context.get("evidence_refs") or context.get("source_refs") or []
        if isinstance(refs, str):
            refs = [refs]
        return [str(x).strip() for x in refs if str(x).strip()]

    @staticmethod
    def _bool(context: Dict[str, Any], key: str) -> bool:
        value = context.get(key)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "y"}

    def classify(self, action: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = dict(context or {})
        key = str(action or "").strip()
        meta = self.ACTIONS.get(key)
        if not meta:
            return {
                "status": "BLOCK",
                "decision": "BLOCK",
                "risk": "HIGH",
                "action": key,
                "reason_code": "unknown_action",
                "rationale": ["Unknown actions default to BLOCK; register the action before execution."],
                "approval_required": False,
                "execution_allowed": False,
            }

        risk = meta["risk"]
        escalators = []
        for flag, reason in (
            ("external_effect", "external_effect"),
            ("financial", "financial_effect"),
            ("destructive", "destructive_effect"),
            ("sensitive", "sensitive_state"),
        ):
            if meta.get(flag) or self._bool(context, flag):
                escalators.append(reason)
        if escalators:
            risk = "HIGH" if any(x in escalators for x in ("external_effect", "financial_effect", "destructive_effect")) else max(risk, "MEDIUM", key=self.RISK_ORDER.get)

        confidence = self._confidence_level(context)
        refs = self._evidence_refs(context)
        evidence_boundary = str(context.get("evidence_boundary") or "").strip()
        evidence_ready = bool(refs) and evidence_boundary not in {"unsupported", "unknown"}
        rationale = []
        decision = "REVIEW"
        approval_required = True
        execution_allowed = False
        reason_code = "consequential_action"

        if risk == "LOW" and evidence_ready and confidence == "high":
            decision = "AUTO_ALLOW"
            approval_required = False
            execution_allowed = True
            reason_code = "low_risk_high_confidence"
            rationale.append("Low-risk internal action with high-confidence, provenance-bound evidence.")
        elif risk == "LOW" and not evidence_ready:
            decision = "REVIEW"
            reason_code = "evidence_not_decision_ready"
            rationale.append("Low-risk action lacks sufficient provenance-bound evidence for automatic handling.")
        elif risk == "MEDIUM" and not (meta.get("sensitive") or self._bool(context, "sensitive")) and evidence_ready and confidence == "high":
            decision = "AUTO_ALLOW"
            approval_required = False
            execution_allowed = True
            reason_code = "bounded_reversible_internal_action"
            rationale.append("Reversible internal action with high-confidence evidence and no sensitive-data escalation.")
        else:
            if risk == "HIGH":
                reason_code = "high_risk_action"
                rationale.append("High-risk or consequential action requires explicit human approval.")
            elif confidence == "low":
                reason_code = "low_confidence"
                rationale.append("Confidence is too low for automatic handling.")
            elif not evidence_ready:
                reason_code = "evidence_not_decision_ready"
                rationale.append("Evidence is missing or not provenance-bounded.")
            else:
                reason_code = "policy_review"
                rationale.append("Policy requires review for this action class.")

        if escalators:
            rationale.append("Escalation factors: " + ", ".join(escalators) + ".")
        return {
            "status": decision,
            "decision": decision,
            "risk": risk,
            "action": key,
            "reason_code": reason_code,
            "confidence": confidence,
            "evidence_ready": evidence_ready,
            "evidence_ref_count": len(refs),
            "evidence_boundary": evidence_boundary or None,
            "external_effect": bool(meta.get("external_effect") or self._bool(context, "external_effect")),
            "financial": bool(meta.get("financial") or self._bool(context, "financial")),
            "destructive": bool(meta.get("destructive") or self._bool(context, "destructive")),
            "reversible": bool(meta.get("reversible")),
            "approval_required": approval_required,
            "execution_allowed": execution_allowed,
            "required_scope": meta["required_scope"],
            "rationale": rationale,
            "evidence_refs": refs,
            "policy_version": "O44-v1.0",
            "decision_boundary": "Governance classification controls execution posture; it does not prove business correctness.",
        }

    def evaluate(self, project_id: str, action: str, context: Optional[Dict[str, Any]] = None,
                 run_id: str | None = None, requested_by: str = "system", create_approval: bool = True) -> Dict[str, Any]:
        context = dict(context or {})
        result = self.classify(action, context)
        approval_id = None
        approval = None
        if result.get("decision") == "REVIEW" and create_approval:
            approval_context = dict(context)
            approval_context.setdefault("project_id", project_id)
            approval_context.setdefault("run_id", run_id or "")
            approval = self.approvals.create(run_id or "", action, approval_context, requested_by=requested_by, ttl_seconds=3600)
            approval_id = approval["approval_id"]
        decision_id = "GOV-" + uuid.uuid4().hex[:12].upper()
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO governance_decisions VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                decision_id, project_id, run_id or "", action, result["decision"], result["risk"],
                result.get("confidence") or "", json.dumps(result.get("evidence_refs") or []),
                json.dumps(result.get("rationale") or []), approval_id, now,
            ),
        )
        self.conn.commit()
        result.update({"decision_id": decision_id, "project_id": project_id, "run_id": run_id, "approval_id": approval_id})
        if approval:
            result["approval"] = approval
        return result

    def pending(self, project_id: str | None = None) -> list[Dict[str, Any]]:
        items = self.approvals.pending()
        if not project_id:
            return items
        out = []
        for item in items:
            payload = item.get("payload") or {}
            if payload.get("project_id") == project_id:
                out.append(item)
        return out

    def decide(self, approval_id: str, principal: Dict[str, Any], decision: str, reason: str = "") -> Dict[str, Any]:
        approval = self.approvals.get(approval_id)
        if not approval:
            return {"status": "NOT_FOUND", "approval_id": approval_id}
        authority = self.authority.can_decide(principal, approval)
        if authority.get("status") != "ALLOW":
            return authority
        return self.approvals.decide(approval_id, decision, principal.get("principal_id", ""), reason)

    def get(self, decision_id: str) -> Dict[str, Any]:
        row = self.conn.execute("SELECT * FROM governance_decisions WHERE decision_id=?", (decision_id,)).fetchone()
        if not row:
            return {"status": "NOT_FOUND", "decision_id": decision_id}
        keys = ["decision_id","project_id","run_id","action","decision","risk","confidence","evidence_refs_json","rationale_json","approval_id","created_at"]
        item = dict(zip(keys, row))
        item["evidence_refs"] = json.loads(item.pop("evidence_refs_json") or "[]")
        item["rationale"] = json.loads(item.pop("rationale_json") or "[]")
        item["status"] = "OK"
        return item

    def list(self, project_id: str | None = None, run_id: str | None = None, limit: int = 50) -> list[Dict[str, Any]]:
        sql = "SELECT decision_id FROM governance_decisions WHERE 1=1"
        params = []
        if project_id:
            sql += " AND project_id=?"; params.append(project_id)
        if run_id:
            sql += " AND run_id=?"; params.append(run_id)
        sql += " ORDER BY created_at DESC LIMIT ?"; params.append(max(1, min(int(limit), 200)))
        ids = [r[0] for r in self.conn.execute(sql, tuple(params)).fetchall()]
        return [self.get(x) for x in ids]

    def close(self):
        try:
            self.approvals.close()
        finally:
            self.conn.close()
