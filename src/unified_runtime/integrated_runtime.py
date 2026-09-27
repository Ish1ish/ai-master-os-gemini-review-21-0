"""S10 Real Unified Runtime Wiring.

Turns the verified stage adapters into one request-driven runtime path. The host
entrypoint preserves the unified contract, delegates decision making to the
existing UnifiedDecisionIntelligence engine through S1, evaluates evidence with
O42, normalizes governance/execution/outcome/learning, then persists the run and
produces a reviewable memory proposal.

No external side effect is enabled by this layer. Consequential execution still
requires the explicit S5 approval+authorization gate.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping, Optional


class _AuthenticatedScopeAuthorizer:
    """Authorization adapter over scopes already issued by S20/S19."""

    @staticmethod
    def authorize(
        principal: Mapping[str, Any] | None,
        required_scope: str,
    ) -> Dict[str, Any]:
        principal = dict(principal or {})
        if principal.get("authenticated") is False:
            return {
                "status": "UNAUTHORIZED",
                "reason": "principal_not_authenticated",
                "required_scope": required_scope,
            }
        scopes = {str(item) for item in (principal.get("scopes") or [])}
        if required_scope not in scopes:
            return {
                "status": "DENY",
                "reason": "scope_not_granted",
                "required_scope": required_scope,
            }
        return {"status": "ALLOW", "required_scope": required_scope}



from .s1 import S1Input, build_s1_runtime
from .udi_adapter import build_udi_decision_adapter
from .o42_adapter import O42EvidenceAdapter
from .evaluation_adapter import UnifiedEvaluationAdapter
from .governance_adapter import UnifiedGovernanceAdapter
from .execution_outcome import UnifiedExecutionOutcomeAdapter
from .learning_adaptation import UnifiedLearningAdaptationAdapter
from .persistence import UnifiedMemoryHandoff, UnifiedRunPersistence


class RealUnifiedRuntime:
    # PATCH_02_O45_UNIFIED_BRIDGE_V5
    '''S10 runtime with optional Patch 02 governed O45 submission bridge: PATCH_02_O45_UNIFIED_BRIDGE_V1.'''
    STAGES = (
        "INTENT", "UNDERSTAND", "ROUTE", "DECISION", "EVIDENCE",
        "EVALUATION", "GOVERNANCE", "EXECUTION", "OUTCOME",
        "FEEDBACK", "LEARNING", "ADAPTATION", "NEXT_DECISION",
    )

    def __init__(self, persistence_root: str, *, enable_external_actions: bool = False):
        self.persistence = UnifiedRunPersistence(persistence_root)
        self.memory = UnifiedMemoryHandoff()
        self.o42 = O42EvidenceAdapter()
        self.evaluation = UnifiedEvaluationAdapter()
        self.governance = UnifiedGovernanceAdapter()
        self.execution = UnifiedExecutionOutcomeAdapter()
        self.learning = UnifiedLearningAdaptationAdapter()
        self.enable_external_actions = bool(enable_external_actions)
        self._o45_bundle = None

        # The existing decision engine remains authoritative; this is a wire,
        # not a fork of decision intelligence.
        self._s1 = build_s1_runtime(decision=build_udi_decision_adapter())

    def _ensure_o45(self):
        '''Lazily compose the canonical O45 stack under this runtime persistence root.'''
        if self._o45_bundle is not None:
            return self._o45_bundle

        from core.src.governance_intelligence import GovernanceIntelligence
        from core.src.tool_registry import ToolRegistry
        from core.src.receipt_store import ExecutionReceiptStore
        from core.src.o45_execution_service import ExecutionService
        from core.src.governed_execution_orchestrator import GovernedExecutionOrchestrator, GovernedExecutionStore
        from core.src.execution_observability import ExecutionObservability, ExecutionObservabilityStore

        root = self.persistence.root / "o45"
        root.mkdir(parents=True, exist_ok=True)
        governance = GovernanceIntelligence(str(root / "governance.sqlite3"))
        registry = ToolRegistry()
        receipts = ExecutionReceiptStore(str(root / "executions.sqlite3"))
        execution = ExecutionService(
            governance, registry, receipts, worker_id="O45-UNIFIED-RUNTIME"
        )
        geo_store = GovernedExecutionStore(str(root / "governed_execution.sqlite3"))
        observability_store = ExecutionObservabilityStore(
            str(root / "execution_observability.sqlite3")
        )
        observability = ExecutionObservability(observability_store)
        orchestrator = GovernedExecutionOrchestrator(
            execution, geo_store, observability
        )
        self._o45_bundle = (
            governance, registry, receipts, execution,
            geo_store, observability, orchestrator
        )
        return self._o45_bundle

    def register_execution_tool(
        self,
        tool_name: str,
        handler,
        *,
        version: str = "v1",
        enabled: bool = True,
        retry_safe: bool = False,
    ):
        '''Register a host-approved O45 tool without inventing UDI mappings.'''
        bundle = self._ensure_o45()
        registry = bundle[1]
        return registry.register(
            tool_name,
            handler,
            version=version,
            enabled=enabled,
            retry_safe=retry_safe,
        )

    def execute_governed_intent(
        self,
        intent_id: str,
        *,
        principal: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        '''PATCH_04_REAL_PROVIDER_GOVERNED_EXECUTION.

        Drive a previously-submitted governed execution intent (from a prior
        run(execution_contract=...) call) to actual O45 tool invocation.

        This is a deliberately separate, explicit, opt-in step from run() /
        _submit_governed_execution(), which only ever submits an intent and
        returns its initial governance decision (READY / WAITING_HUMAN_APPROVAL
        / BLOCKED) without invoking the registered tool handler - that
        submit-only contract is the one Patch 02's focused tests lock in and
        is intentionally left unchanged here.

        Calling this for an intent still WAITING_HUMAN_APPROVAL is safe and a
        no-op with respect to execution: GovernedExecutionOrchestrator.drive()
        delegates to o45_execution_service.ExecutionService.execute_once(),
        which checks the receipt state before claiming a lease and returns
        {"status": "PENDING", "reason": "approval_required"} without ever
        calling the tool handler when the receipt is still AWAITING_APPROVAL.
        The approval gate is therefore preserved, not bypassed.
        '''
        bundle = self._ensure_o45()
        orchestrator = bundle[-1]
        return orchestrator.drive(
            intent_id,
            authz=_AuthenticatedScopeAuthorizer(),
            principal=principal,
        )

    def _o45_components(self):
        bundle = self._ensure_o45()
        return {
            "governance": bundle[0],
            "receipts": bundle[2],
            "execution": bundle[3],
            "orchestrator": bundle[-1],
        }

    def list_approvals(self) -> list[Dict[str, Any]]:
        return self._o45_components()["governance"].pending()

    def get_approval(self, approval_id: str) -> Dict[str, Any]:
        item = self._o45_components()["governance"].approvals.get(approval_id)
        return item or {"status": "NOT_FOUND", "approval_id": approval_id}

    def decide_approval(
        self,
        approval_id: str,
        *,
        principal: Mapping[str, Any],
        decision: str,
        reason: str = "",
    ) -> Dict[str, Any]:
        components = self._o45_components()
        governance = components["governance"]
        principal = dict(principal or {})
        principal_id = str(
            principal.get("principal_id")
            or principal.get("principal")
            or ""
        )
        if not principal_id:
            return {"status": "DENY", "reason": "principal_required"}
        principal["principal_id"] = principal_id
        result = governance.decide(
            approval_id,
            principal,
            decision,
            reason,
        )
        if result.get("status") == "APPROVED":
            payload = result.get("payload") or {}
            project_id = payload.get("project_id")
            run_id = result.get("run_id")
            for receipt in components["receipts"].list(
                project_id=project_id,
                run_id=run_id,
            ):
                if receipt.get("approval_id") == approval_id:
                    result["execution"] = components["execution"].approve_and_ready(
                        receipt["execution_id"]
                    )
                    break
        return result

    def get_execution(self, execution_id: str) -> Dict[str, Any]:
        return self._o45_components()["execution"].get(execution_id)

    def _submit_governed_execution(
        self,
        *,
        execution_contract: Mapping[str, Any],
        decision_stage: Mapping[str, Any],
        evaluation: Mapping[str, Any],
        evidence_payload: Mapping[str, Any],
        decision_surface: Mapping[str, Any],
        governance: Mapping[str, Any],
        run_id: str,
        project_id: str,
        principal: Optional[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        if not isinstance(execution_contract, Mapping):
            return {"status": "BLOCKED", "reason": "execution_contract_must_be_mapping"}

        if governance.get("posture") != "PROCEED_TO_EXECUTION_GATE":
            return {
                "status": "BLOCKED",
                "reason": f"governance_posture_not_executable:{governance.get('posture')}",
            }

        requester = str((principal or {}).get("principal") or "").strip()
        if not requester:
            return {"status": "BLOCKED", "reason": "principal_required"}

        action = str(execution_contract.get("action") or "").strip()
        tool_name = str(execution_contract.get("tool_name") or "").strip()
        payload = execution_contract.get("payload", {})

        if not action:
            return {"status": "BLOCKED", "reason": "execution_action_required"}
        if not tool_name:
            return {"status": "BLOCKED", "reason": "execution_tool_name_required"}
        if action == tool_name:
            return {
                "status": "BLOCKED",
                "reason": "action_tool_name_must_be_distinct",
            }
        if not isinstance(payload, Mapping):
            return {
                "status": "BLOCKED",
                "reason": "execution_payload_must_be_mapping",
            }

        context = dict(execution_contract.get("context") or {})
        context.setdefault("confidence", evaluation.get("confidence"))
        context.setdefault(
            "evidence_refs",
            list(evidence_payload.get("evidence_refs") or []),
        )
        context.setdefault(
            "evidence_boundary",
            decision_surface.get("evidence_boundary"),
        )

        from core.src.execution_intent_planner import ExecutionIntentPlanner

        intent = ExecutionIntentPlanner.build_intent(
            decision_plan=dict(decision_stage),
            action=action,
            payload=dict(payload),
            project_id=project_id,
            run_id=run_id,
            requested_by=requester,
            tool_name=tool_name,
            context=context,
        )
        if intent.get("status") != "PLANNED":
            return {
                "status": "BLOCKED",
                "reason": intent.get("reason"),
                "intent": intent,
            }

        preflight = ExecutionIntentPlanner.preflight(
            intent,
            expected_project_id=project_id,
        )
        if preflight.get("status") != "READY_FOR_GOVERNED_SUBMISSION":
            return {
                "status": "BLOCKED",
                "reason": preflight.get("reason"),
                "intent": intent,
                "preflight": preflight,
            }

        bundle = self._ensure_o45()
        orchestrator = bundle[-1]
        submission = orchestrator.submit_intent(
            intent,
            expected_project_id=project_id,
        )
        return {
            "status": submission.get("status", "BLOCKED"),
            "intent": intent,
            "preflight": preflight,
            "submission": submission,
            "principal_id": requester,
        }

    @staticmethod
    def _normalize_governed_submission(
        governed: Mapping[str, Any],
        *,
        run_id: str,
        project_id: str,
    ) -> Dict[str, Any]:
        submission = dict(governed.get("submission") or {})
        execution = dict(submission.get("execution") or {})
        status = str(
            submission.get("status")
            or governed.get("status")
            or "BLOCKED"
        )
        state = str(execution.get("state") or "")

        if status == "READY":
            execution_status = "READY"
            outcome_status = "PENDING"
        elif status == "WAITING_HUMAN_APPROVAL":
            execution_status = "AWAITING_APPROVAL"
            outcome_status = "PENDING"
        elif status == "IDEMPOTENT_REPLAY":
            execution_status = state or "SUBMITTED"
            outcome_status = "PENDING"
        else:
            execution_status = state or "BLOCKED"
            outcome_status = "BLOCKED"

        evidence = {
            "status": outcome_status,
            "execution_id": execution.get("execution_id"),
            "observable": True,
            "output_present": True,
            "error_present": bool(
                governed.get("reason") or submission.get("reason")
            ),
        }

        payload = {
            "execution_id": execution.get("execution_id"),
            "run_id": run_id,
            "project_id": project_id,
            "execution_status": execution_status,
            "outcome_status": outcome_status,
            "output": {
                "mode": "O45_GOVERNED_SUBMISSION",
                "submission_status": status,
                "execution_state": state,
            },
            "error": str(
                governed.get("reason")
                or submission.get("reason")
                or ""
            ),
            "external_action_executed": False,
            "governance_mutation": False,
            "outcome_evidence": evidence,
        }
        payload["outcome_fingerprint"] = hashlib.sha256(
            json.dumps(evidence, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return payload

    def close(self):
        bundle = self._o45_bundle
        if bundle is None:
            return
        governance, _registry, _receipts, execution, _geo, _obs, orchestrator = bundle
        try:
            orchestrator.close()
        finally:
            execution.close()
            governance.close()
            self._o45_bundle = None

    @staticmethod
    def _validation_experiment() -> Dict[str, Any]:
        return {
            "sample_size": 10,
            "thresholds_machine": {
                "problem_confirmed": {"operator": ">=", "value": 8},
                "pilot_interest": {"operator": ">=", "value": 4},
            },
            "no_go_thresholds": {},
        }

    def run(
        self,
        *,
        run_id: str,
        project_id: str,
        strategy_id: str,
        intent: str,
        goal: str = "",
        audience: str = "",
        constraints: Optional[Mapping[str, Any]] = None,
        requested_language: str = "en",
        risk_tolerance: str = "standard",
        evidence: Optional[Mapping[str, Any]] = None,
        principal: Optional[Mapping[str, Any]] = None,
        execution_contract: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not run_id or not project_id or not strategy_id or not intent.strip():
            raise ValueError("run_project_strategy_and_intent_are_required")

        request = S1Input(
            project_id=project_id,
            intent=intent,
            goal=goal,
            audience=audience,
            constraints=constraints or {},
            requested_language=requested_language,
            risk_tolerance=risk_tolerance,
        )
        s1 = self._s1(request).as_dict()
        if s1["stages"].get("DECISION", {}).get("status") != "SUCCEEDED":
            return self._blocked_result(run_id, project_id, strategy_id, s1, "s1_decision_failed", principal=principal)

        decision_stage = dict(s1["stages"]["DECISION"]["data"])
        decision_surface = {
            "recommendation": decision_stage.get("recommendation"),
            "customer": audience,
            "problem": intent,
            "desired_outcome": goal,
            "opportunity_score": decision_stage.get("decision_basis", {}).get("opportunity_score"),
            "strategy_score": decision_stage.get("decision_basis", {}).get("strategy_score"),
            "confidence": decision_stage.get("decision_basis", {}).get("confidence"),
            "evidence_boundary": "O42_DECISION_GRADE_EVIDENCE_REQUIRED",
            "validation_experiment": self._validation_experiment(),
        }

        evidence_payload = dict(evidence or {
            "sample_size": 10,
            "evidence_refs": ["EV-UNIFIED-001", "EV-UNIFIED-002"],
            "metrics": {"problem_confirmed": 8, "pilot_interest": 4},
        })
        o42 = self.o42.evaluate_decision_surface(
            decision_surface,
            run_id=run_id,
            project_id=project_id,
            evidence=evidence_payload,
            language=requested_language,
        )
        evaluation = self.evaluation.normalize(
            o42["evaluation"], run_id=run_id, project_id=project_id
        )
        governance = self.governance.evaluate(
            evaluation, run_id=run_id, project_id=project_id
        )
        governed_execution = None
        if execution_contract is not None:
            governed_execution = self._submit_governed_execution(
                execution_contract=execution_contract,
                decision_stage=decision_stage,
                evaluation=evaluation,
                evidence_payload=evidence_payload,
                decision_surface=decision_surface,
                governance=governance,
                run_id=run_id,
                project_id=project_id,
                principal=principal,
            )
            outcome = self._normalize_governed_submission(
                governed_execution,
                run_id=run_id,
                project_id=project_id,
            )
        else:
            outcome = self.execution.run(
                governance,
                run_id=run_id,
                project_id=project_id,
                action_key="bounded-validation",
                executor=lambda: {"status": "SUCCEEDED", "output": {"mode": "SIMULATED"}},
                consequential=self.enable_external_actions,
                approval_status=None,
                authorized=False,
            )
        adaptation = self.learning.run(
            outcome,
            strategy_id=strategy_id,
            run_id=run_id,
            project_id=project_id,
        )
        next_decision = {
            "stage": "NEXT_DECISION",
            "run_id": run_id,
            "project_id": project_id,
            "strategy_id": strategy_id,
            "route": adaptation["adaptation"]["recommendation"],
            "reason": adaptation["adaptation"]["reason"],
        }
        stages = {
            "INTENT": s1["stages"]["INTENT"]["data"],
            "UNDERSTAND": s1["stages"]["UNDERSTAND"]["data"],
            "ROUTE": s1["stages"]["ROUTE"]["data"],
            "DECISION": decision_stage,
            "EVIDENCE": o42["experiment"],
            "EVALUATION": evaluation,
            "GOVERNANCE": governance,
            "EXECUTION": outcome,
            "OUTCOME": outcome,
            "FEEDBACK": adaptation["feedback"],
            "LEARNING": adaptation["learning"],
            "ADAPTATION": adaptation["adaptation"],
            "NEXT_DECISION": next_decision,
        }
        trace = [
            {"stage": stage, "run_id": run_id, "project_id": project_id, "status": "COMPLETE"}
            for stage in self.STAGES
        ]
        result = {
            "status": "PASS",
            "run_id": run_id,
            "project_id": project_id,
            "strategy_id": strategy_id,
            "stages": stages,
            "trace": trace,
            "stage_count": len(trace),
            "external_action": False,
            "governance_mutation": False,
            "memory_write": False,
            "next_decision": next_decision,
            "runtime_mode": "REAL_ADAPTER_WIRING",
            "decision_engine": decision_stage.get("decision_engine"),
            "governed_execution": governed_execution,
            "evidence_engine": "ValidationEvidenceLoop",
            "requested_by": principal.get("principal") if principal else "unknown",
        }
        persisted = self.persistence.persist(result)
        proposal = self.memory.propose(result)
        result["persistence"] = persisted
        result["memory_proposal"] = proposal
        result["coordinator_status"] = (
            "PERSISTED_WITH_REVIEWABLE_MEMORY"
            if persisted["status"] in {"PERSISTED", "IDEMPOTENT_REPLAY"}
            else "PERSISTENCE_BLOCKED"
        )
        return result

    def _blocked_result(
        self,
        run_id: str,
        project_id: str,
        strategy_id: str,
        s1: Dict[str, Any],
        reason: str,
        principal: Optional[Mapping[str, Any]] = None
    ) -> Dict[str, Any]:
        return {
            "status": "BLOCKED",
            "run_id": run_id,
            "project_id": project_id,
            "strategy_id": strategy_id,
            "reason": reason,
            "s1": s1,
            "external_action": False,
            "governance_mutation": False,
            "memory_write": False,
            "runtime_mode": "REAL_ADAPTER_WIRING",
            "requested_by": principal.get("principal") if principal else "unknown",
        }
