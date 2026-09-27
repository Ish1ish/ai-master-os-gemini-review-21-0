from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .execution_intent_planner import ExecutionIntentPlanner
from .o45_execution_service import canonical_request, request_hash
from .execution_observability import ExecutionObservability


SCHEMA_VERSION = "GEO-v1.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def intent_fingerprint(intent: Dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(intent).encode("utf-8")).hexdigest()


class GovernedExecutionStore:
    """Durable intent -> execution binding and lifecycle audit."""

    STATES = {
        "SUBMITTED",
        "WAITING_HUMAN_APPROVAL",
        "READY",
        "RUNNING",
        "SUCCEEDED",
        "FAILED_RETRYABLE",
        "FAILED_TERMINAL",
        "BLOCKED",
        "RECOVERY_REQUIRED",
        "CANCELLED",
    }

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.RLock()
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS governed_execution_bindings(
                intent_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL UNIQUE,
                idempotency_key TEXT NOT NULL UNIQUE,
                project_id TEXT NOT NULL,
                run_id TEXT,
                decision_plan_id TEXT NOT NULL,
                intent_fingerprint TEXT NOT NULL,
                request_hash TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS governed_execution_events(
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                intent_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                from_state TEXT,
                to_state TEXT,
                execution_id TEXT,
                metadata_json TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_geo_project ON governed_execution_bindings(project_id, created_at)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_geo_events ON governed_execution_events(intent_id, event_id)")
        self.conn.commit()

    def _row(self, row: Optional[tuple]) -> Optional[Dict[str, Any]]:
        if not row:
            return None
        keys = [
            "intent_id", "execution_id", "idempotency_key", "project_id", "run_id",
            "decision_plan_id", "intent_fingerprint", "request_hash", "state",
            "created_at", "updated_at",
        ]
        return dict(zip(keys, row))

    def get(self, intent_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self.conn.execute(
                "SELECT * FROM governed_execution_bindings WHERE intent_id=?", (intent_id,)
            ).fetchone()
        return self._row(row)

    def by_idempotency(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self.conn.execute(
                "SELECT * FROM governed_execution_bindings WHERE idempotency_key=?", (key,)
            ).fetchone()
        return self._row(row)

    def create(self, *, intent_id: str, execution_id: str, idempotency_key: str,
               project_id: str, run_id: Optional[str], decision_plan_id: str,
               fingerprint: str, request_digest: str, state: str) -> Dict[str, Any]:
        if state not in self.STATES:
            raise ValueError("invalid_governed_execution_state")
        now = utc_now()
        with self._lock:
            try:
                self.conn.execute(
                    """
                    INSERT INTO governed_execution_bindings(
                        intent_id,execution_id,idempotency_key,project_id,run_id,
                        decision_plan_id,intent_fingerprint,request_hash,state,created_at,updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        intent_id, execution_id, idempotency_key, project_id, run_id,
                        decision_plan_id, fingerprint, request_digest, state, now, now,
                    ),
                )
                self._event_unlocked(intent_id, "SUBMITTED", None, state, execution_id, {
                    "request_hash": request_digest,
                    "intent_fingerprint": fingerprint,
                })
                self.conn.commit()
            except sqlite3.IntegrityError:
                self.conn.rollback()
                existing = self.get(intent_id)
                if existing:
                    return existing
                raise
        return self.get(intent_id)

    def transition(self, intent_id: str, state: str, *, execution_id: Optional[str] = None,
                   metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if state not in self.STATES:
            raise ValueError("invalid_governed_execution_state")
        with self._lock:
            row = self.conn.execute(
                "SELECT state,execution_id FROM governed_execution_bindings WHERE intent_id=?", (intent_id,)
            ).fetchone()
            if not row:
                raise KeyError("governed_execution_not_found")
            previous, existing_execution_id = row
            eid = execution_id or existing_execution_id
            self.conn.execute(
                "UPDATE governed_execution_bindings SET state=?,execution_id=?,updated_at=? WHERE intent_id=?",
                (state, eid, utc_now(), intent_id),
            )
            self._event_unlocked(intent_id, "STATE_CHANGED", previous, state, eid, metadata or {})
            self.conn.commit()
        return self.get(intent_id)

    def _event_unlocked(self, intent_id: str, event_type: str, from_state: Optional[str],
                        to_state: Optional[str], execution_id: Optional[str], metadata: Dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT INTO governed_execution_events(
                intent_id,event_type,from_state,to_state,execution_id,metadata_json,created_at
            ) VALUES(?,?,?,?,?,?,?)
            """,
            (intent_id, event_type, from_state, to_state, execution_id, canonical_json(metadata), utc_now()),
        )

    def events(self, intent_id: str) -> list[Dict[str, Any]]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT event_id,event_type,from_state,to_state,execution_id,metadata_json,created_at "
                "FROM governed_execution_events WHERE intent_id=? ORDER BY event_id",
                (intent_id,),
            ).fetchall()
        return [
            {
                "event_id": r[0], "event_type": r[1], "from_state": r[2], "to_state": r[3],
                "execution_id": r[4], "metadata": json.loads(r[5] or "{}"), "created_at": r[6],
            }
            for r in rows
        ]

    def close(self) -> None:
        with self._lock:
            if getattr(self, "conn", None) is not None:
                self.conn.close()
                self.conn = None


class GovernedExecutionOrchestrator:
    """Turns a validated Execution Intent into a governed O45 execution.

    The orchestrator never bypasses governance and never calls a tool handler.
    It binds the exact intent to the canonical O45 request, persists the binding,
    and delegates execution to O45 for idempotency, approval, leases, recovery,
    and audit.
    """

    def __init__(self, execution_service, store: GovernedExecutionStore, observability: Optional[ExecutionObservability] = None):
        self.execution = execution_service
        self.store = store
        self.observability = observability

    @staticmethod
    def _validate_intent_shape(intent: Dict[str, Any]) -> Optional[str]:
        if not isinstance(intent, dict):
            return "intent_must_be_object"
        required = (
            "status", "intent_id", "decision_plan_id", "project_id", "run_id",
            "requested_by", "action", "tool_name", "payload", "execution_request",
            "governance_authority",
        )
        for field in required:
            if field not in intent:
                return f"{field}_required"
        if intent.get("status") != "PLANNED":
            return "intent_not_planned"
        if intent.get("governance_authority") != "POLICY_AND_GOVERNANCE_REMAIN_AUTHORITATIVE":
            return "governance_authority_invalid"
        if not isinstance(intent.get("payload"), dict):
            return "payload_must_be_object"
        request = intent.get("execution_request")
        if not isinstance(request, dict):
            return "execution_request_missing"
        return None

    @staticmethod
    def _state_from_receipt(receipt: Dict[str, Any], default: str = "SUBMITTED") -> str:
        state = receipt.get("state") if isinstance(receipt, dict) else None
        mapping = {
            "AWAITING_APPROVAL": "WAITING_HUMAN_APPROVAL",
            "PENDING_GOVERNANCE": "SUBMITTED",
            "READY": "READY",
            "RUNNING": "RUNNING",
            "SUCCEEDED": "SUCCEEDED",
            "FAILED_RETRYABLE": "FAILED_RETRYABLE",
            "FAILED_TERMINAL": "FAILED_TERMINAL",
            "BLOCKED": "BLOCKED",
            "RECOVERY_REQUIRED": "RECOVERY_REQUIRED",
            "CANCELLED": "CANCELLED",
        }
        return mapping.get(state, default)

    def _validate_binding(self, intent: Dict[str, Any], *, expected_project_id: Optional[str]) -> Dict[str, Any]:
        err = self._validate_intent_shape(intent)
        if err:
            return {"status": "BLOCKED", "reason": err}
        pf = ExecutionIntentPlanner.preflight(intent, expected_project_id=expected_project_id)
        if pf.get("status") != "READY_FOR_GOVERNED_SUBMISSION":
            return pf
        request = intent["execution_request"]
        expected = canonical_request(
            intent["project_id"], intent["run_id"], intent["action"],
            intent["tool_name"], intent["payload"],
        )
        if request.get("project_id") != expected["project_id"]:
            return {"status": "BLOCKED", "reason": "request_project_binding_mismatch"}
        if request.get("run_id") != expected["run_id"]:
            return {"status": "BLOCKED", "reason": "request_run_binding_mismatch"}
        if request.get("action") != expected["action"]:
            return {"status": "BLOCKED", "reason": "request_action_binding_mismatch"}
        if request.get("tool_name") != expected["tool_name"]:
            return {"status": "BLOCKED", "reason": "request_tool_binding_mismatch"}
        if request.get("payload") != expected["payload"]:
            return {"status": "BLOCKED", "reason": "request_payload_binding_mismatch"}
        if request.get("idempotency_key") != intent["execution_request"].get("idempotency_key"):
            return {"status": "BLOCKED", "reason": "request_idempotency_missing"}
        return {
            "status": "READY",
            "request_hash": request_hash(expected),
            "intent_fingerprint": intent_fingerprint(intent),
        }

    def submit_intent(self, intent: Dict[str, Any], *, expected_project_id: Optional[str] = None) -> Dict[str, Any]:
        binding_check = self._validate_binding(intent, expected_project_id=expected_project_id)
        if binding_check.get("status") != "READY":
            return binding_check

        intent_id = str(intent["intent_id"])
        if self.observability:
            self.observability.record_decision(
                project_id=intent["project_id"], run_id=intent.get("run_id"),
                decision_plan_id=intent["decision_plan_id"], intent_id=intent_id,
                status=intent["decision_plan"].get("status", "RECOMMEND") if isinstance(intent.get("decision_plan"), dict) else "RECOMMEND",
                action=intent["action"],
                decision_basis=(intent.get("decision_basis") or intent.get("decision_plan", {}).get("decision_basis", {})) if isinstance(intent.get("decision_plan"), dict) else {},
                evidence_refs=(intent.get("context") or {}).get("evidence_refs", []),
            )
            self.observability.record_intent(
                project_id=intent["project_id"], run_id=intent.get("run_id"),
                decision_plan_id=intent["decision_plan_id"], intent_id=intent_id,
                status=intent.get("status", "PLANNED"), intent_fingerprint_value=binding_check["intent_fingerprint"],
            )
        existing = self.store.get(intent_id)
        fp = binding_check["intent_fingerprint"]
        digest = binding_check["request_hash"]
        if existing:
            if existing["intent_fingerprint"] != fp or existing["request_hash"] != digest:
                return {"status": "CONFLICT", "reason": "intent_binding_conflict", "intent_id": intent_id}
            execution = self.execution.get(existing["execution_id"])
            return {
                "status": "IDEMPOTENT_REPLAY",
                "intent_id": intent_id,
                "execution": execution,
                "binding": existing,
            }

        req = intent["execution_request"]
        out = self.execution.request(
            project_id=req["project_id"],
            run_id=req.get("run_id"),
            action=req["action"],
            tool_name=req["tool_name"],
            payload=req["payload"],
            context=req.get("context") or {},
            idempotency_key=req["idempotency_key"],
            requested_by=req["requested_by"],
        )
        if out.get("status") not in {"ACCEPTED"}:
            return {"status": out.get("status", "BLOCKED"), "reason": out.get("reason"), "execution": out.get("execution")}
        execution = out.get("execution") or {}
        state = self._state_from_receipt(execution)
        binding = self.store.create(
            intent_id=intent_id,
            execution_id=execution["execution_id"],
            idempotency_key=req["idempotency_key"],
            project_id=intent["project_id"],
            run_id=intent["run_id"],
            decision_plan_id=intent["decision_plan_id"],
            fingerprint=fp,
            request_digest=digest,
            state=state,
        )
        if self.observability:
            self.observability.record_execution(
                project_id=intent["project_id"], run_id=intent.get("run_id"),
                decision_plan_id=intent["decision_plan_id"], intent_id=intent_id,
                execution_id=execution["execution_id"], state=state, phase="submitted",
            )
        if state == "WAITING_HUMAN_APPROVAL":
            status = "WAITING_HUMAN_APPROVAL"
        elif state == "READY":
            status = "READY"
        elif state == "BLOCKED":
            status = "BLOCKED"
        else:
            status = "SUBMITTED"
        return {"status": status, "intent_id": intent_id, "execution": execution, "binding": binding}

    def drive(self, intent_id: str, *, authz=None, principal: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        binding = self.store.get(intent_id)
        if not binding:
            return {"status": "NOT_FOUND", "intent_id": intent_id}
        execution_id = binding["execution_id"]
        if self.observability:
            self.observability.record_execution(
                project_id=binding["project_id"], run_id=binding.get("run_id"),
                decision_plan_id=binding["decision_plan_id"], intent_id=intent_id,
                execution_id=execution_id, state="RUNNING", phase="started",
            )
        result = self.execution.execute_once(execution_id, authz=authz, principal=principal)
        execution = result.get("execution") or self.execution.get(execution_id)
        state = self._state_from_receipt(execution, default=result.get("status", "BLOCKED"))
        if result.get("status") == "PENDING" and result.get("reason") == "approval_required":
            state = "WAITING_HUMAN_APPROVAL"
        if state in GovernedExecutionStore.STATES:
            self.store.transition(intent_id, state, execution_id=execution_id, metadata={"execution_status": result.get("status")})
        if self.observability:
            self.observability.record_execution(
                project_id=binding["project_id"], run_id=binding.get("run_id"),
                decision_plan_id=binding["decision_plan_id"], intent_id=intent_id,
                execution_id=execution_id, state=state, phase="finished",
            )
            self.observability.record_outcome(
                project_id=binding["project_id"], run_id=binding.get("run_id"),
                decision_plan_id=binding["decision_plan_id"], intent_id=intent_id,
                execution_id=execution_id, expected_status="RECOMMEND",
                actual_status=execution.get("state", state) if isinstance(execution, dict) else state,
                outcome_status=state, success=state == "SUCCEEDED",
                evidence_refs=[], result=(execution.get("result") if isinstance(execution, dict) else None),
                error=(execution.get("error") if isinstance(execution, dict) else None),
            )
        status_map = {
            "WAITING_HUMAN_APPROVAL": "WAITING_HUMAN_APPROVAL",
            "SUCCEEDED": "SUCCEEDED",
            "AWAITING_APPROVAL": "WAITING_HUMAN_APPROVAL",
            "RECOVERY_REQUIRED": "RECOVERY_REQUIRED",
            "FAILED_RETRYABLE": "FAILED_RETRYABLE",
            "FAILED_TERMINAL": "FAILED_TERMINAL",
            "BLOCKED": "BLOCKED",
            "CANCELLED": "CANCELLED",
            "READY": "READY",
            "RUNNING": "RUNNING",
        }
        return {
            "status": status_map.get(state, result.get("status", "BLOCKED")),
            "intent_id": intent_id,
            "execution": execution,
            "binding": self.store.get(intent_id),
        }

    def approve_and_drive(self, intent_id: str, *, authz=None, principal: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        binding = self.store.get(intent_id)
        if not binding:
            return {"status": "NOT_FOUND", "intent_id": intent_id}
        approved = self.execution.approve_and_ready(binding["execution_id"])
        if approved.get("state") != "READY":
            return {"status": "WAITING_HUMAN_APPROVAL", "intent_id": intent_id, "approval": approved, "binding": self.store.get(intent_id)}
        self.store.transition(intent_id, "READY", metadata={"approval": "validated"})
        return self.drive(intent_id, authz=authz, principal=principal)

    def recover_expired(self, now_epoch=None) -> list[Dict[str, Any]]:
        return self.execution.recover_expired(now_epoch=now_epoch)

    def retry(self, intent_id: str) -> Dict[str, Any]:
        binding = self.store.get(intent_id)
        if not binding:
            return {"status": "NOT_FOUND", "intent_id": intent_id}
        result = self.execution.retry(binding["execution_id"])
        execution = result.get("execution") or self.execution.get(binding["execution_id"])
        state = self._state_from_receipt(execution, default=result.get("status", "BLOCKED"))
        if state in GovernedExecutionStore.STATES:
            self.store.transition(intent_id, state, metadata={"retry_status": result.get("status")})
        return {"status": result.get("status", "BLOCKED"), "intent_id": intent_id, "execution": execution, "binding": self.store.get(intent_id)}

    def cancel(self, intent_id: str) -> Dict[str, Any]:
        binding = self.store.get(intent_id)
        if not binding:
            return {"status": "NOT_FOUND", "intent_id": intent_id}
        result = self.execution.cancel(binding["execution_id"])
        execution = result.get("execution") or self.execution.get(binding["execution_id"])
        state = self._state_from_receipt(execution, default="CANCELLED")
        if state in GovernedExecutionStore.STATES:
            self.store.transition(intent_id, state)
        return {"status": result.get("status", "BLOCKED"), "intent_id": intent_id, "execution": execution, "binding": self.store.get(intent_id)}

    def events(self, intent_id: str) -> list[Dict[str, Any]]:
        return self.store.events(intent_id)

    def close(self) -> None:
        self.store.close()
        if self.observability:
            self.observability.close()
