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
        self._o42_store = None
        self._o42_service = None
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

    def _ensure_o42(self):
        """Compose the durable O42 service under the Unified Runtime root."""
        if self._o42_service is not None:
            return self._o42_service

        from core.src.experiment_store import ExperimentStore
        from core.src.experiments import ExperimentService

        root = self.persistence.root / "o42"
        root.mkdir(parents=True, exist_ok=True)
        self._o42_store = ExperimentStore(str(root / "experiments.sqlite3"))
        # memory_runtime=None preserves the S21 contract: O42 can evaluate and
        # learn, but this canonical surface never performs an automatic memory write.
        self._o42_service = ExperimentService(
            self._o42_store,
            jobs=None,
            memory_runtime=None,
        )
        return self._o42_service

    def _ensure_durable_experiment(
        self,
        definition: Mapping[str, Any],
        *,
        run_id: str,
        project_id: str,
    ) -> Dict[str, Any]:
        service = self._ensure_o42()
        experiment_id = str(definition.get("experiment_id") or "").strip()
        if not experiment_id:
            raise ValueError("experiment_id_required")
        existing = service.get(experiment_id)
        if existing and existing.get("status") != "NOT_FOUND":
            if existing.get("run_id") != run_id or existing.get("project_id") != project_id:
                raise ValueError("experiment_identity_conflict")
            return existing
        return self._o42_store.create(dict(definition), project_id, run_id=run_id)

    def get_experiment(self, experiment_id: str) -> Dict[str, Any]:
        return self._ensure_o42().get(experiment_id)

    def list_experiments(self, project_id: str | None = None, limit: int = 50) -> list[Dict[str, Any]]:
        return self._ensure_o42().list(project_id=project_id, limit=limit)["experiments"]

    def record_experiment_evidence(
        self,
        experiment_id: str,
        evidence: Mapping[str, Any],
    ) -> Dict[str, Any]:
        return self._ensure_o42().record_evidence(experiment_id, dict(evidence))

    def evaluate_experiment(self, experiment_id: str) -> Dict[str, Any]:
        return self._ensure_o42().evaluate(experiment_id)

    def get_learning_context(
        self,
        project_id: str,
        current_experiment_id: str | None = None,
    ) -> Dict[str, Any]:
        return self._ensure_o42().get_learning_context(
            project_id,
            current_experiment_id=current_experiment_id,
        )

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
        research_tool_allowlist = {
            "provider.research.live",
            "provider.research.synthesis",
            "provider.research.workflow",
        }
        if (
            action == "read_only_market_research"
            and tool_name not in research_tool_allowlist
        ):
            return {
                "status": "BLOCKED",
                "reason": "research_action_tool_binding_invalid",
            }

        # Bootstrap is limited to the read-only research action and an explicit
        # allowlist of provider tools. This supports evidence acquisition,
        # source-grounded synthesis, and their combined workflow before
        # decision-grade market evidence exists. O45 still independently
        # classifies and authorizes each registered tool.
        research_bootstrap = (
            action == "read_only_market_research"
            and tool_name in research_tool_allowlist
        )
        # A generated plan is an internal draft only. This exact pair may be
        # bootstrapped from the user's goal and prior research because it has
        # no external effect, does not spend funds, and does not execute tasks.
        plan_bootstrap = (
            action == "generate_internal_draft"
            and tool_name == "provider.project.plan"
        )
        workspace_read_tool = tool_name == "provider.project.workspace.read"
        workspace_write_tool = tool_name == "provider.project.workspace.write"
        workspace_read_bootstrap = (
            action == "read_only_inspection" and workspace_read_tool
        )
        workspace_write_bootstrap = (
            action == "update_project_workspace" and workspace_write_tool
        )
        if (
            (workspace_read_tool and action != "read_only_inspection")
            or (workspace_write_tool and action != "update_project_workspace")
            or (action == "update_project_workspace" and not workspace_write_tool)
        ):
            return {
                "status": "BLOCKED",
                "reason": "project_workspace_action_tool_binding_invalid",
            }
        if workspace_read_tool:
            payload = dict(payload)
            operation = str(payload.get("operation") or "").strip().lower()
            if operation == "get" and str(payload.get("project_id") or "") != project_id:
                return {
                    "status": "BLOCKED",
                    "reason": "project_workspace_project_binding_invalid",
                }
            payload["requested_by"] = requester
        if workspace_write_tool:
            payload = dict(payload)
            if str(payload.get("project_id") or "") != project_id:
                return {
                    "status": "BLOCKED",
                    "reason": "project_workspace_project_binding_invalid",
                }
            payload["requested_by"] = requester

        bootstrap_allowed = (
            research_bootstrap
            or plan_bootstrap
            or workspace_read_bootstrap
            or workspace_write_bootstrap
        )
        upstream_posture = str(governance.get("posture") or "UNKNOWN")
        if (
            upstream_posture != "PROCEED_TO_EXECUTION_GATE"
            and not bootstrap_allowed
        ):
            return {
                "status": "BLOCKED",
                "reason": f"governance_posture_not_executable:{upstream_posture}",
            }

        context = dict(execution_contract.get("context") or {})
        if bootstrap_allowed:
            # These signals authorize a bounded requested operation; they do not
            # imply market claims are true or that a project update was validated.
            context["confidence"] = "high"
            context.setdefault("evidence_refs", [f"user_request:{run_id}"])
            if research_bootstrap:
                context["evidence_boundary"] = "user_request_scope_only"
            elif plan_bootstrap:
                context["evidence_boundary"] = "user_goal_and_research_scope_only"
            elif workspace_read_bootstrap:
                context["evidence_boundary"] = "project_workspace_scope_only"
            else:
                context["evidence_boundary"] = "project_workspace_mutation_scope_only"
        else:
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
        result = {
            "status": submission.get("status", "BLOCKED"),
            "intent": intent,
            "preflight": preflight,
            "submission": submission,
            "principal_id": requester,
        }
        if research_bootstrap:
            result["execution_path"] = "READ_ONLY_EVIDENCE_ACQUISITION"
            result["upstream_governance_posture"] = upstream_posture
        if plan_bootstrap:
            result["execution_path"] = "INTERNAL_DRAFT_BOOTSTRAP"
            result["upstream_governance_posture"] = upstream_posture
        if workspace_read_bootstrap:
            result["execution_path"] = "PROJECT_WORKSPACE_READ"
            result["upstream_governance_posture"] = upstream_posture
        if workspace_write_bootstrap:
            result["execution_path"] = "PROJECT_WORKSPACE_REVISIONED_WRITE"
            result["upstream_governance_posture"] = upstream_posture
        return result

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
        try:
            if bundle is not None:
                governance, _registry, _receipts, execution, _geo, _obs, orchestrator = bundle
                try:
                    orchestrator.close()
                finally:
                    execution.close()
                    governance.close()
                    self._o45_bundle = None
        finally:
            if self._o42_store is not None:
                self._o42_store.close()
                self._o42_store = None
                self._o42_service = None

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
            "sample_size": 0,
            "evidence_refs": [],
            "metrics": {},
        })
        definition = self.o42.build_experiment(
            decision_surface,
            run_id=run_id,
            project_id=project_id,
            language=requested_language,
        )
        durable_experiment = self._ensure_durable_experiment(
            definition,
            run_id=run_id,
            project_id=project_id,
        )
        if evidence is not None:
            saved = self.record_experiment_evidence(
                durable_experiment["experiment_id"],
                evidence_payload,
            )
            if saved.get("status") in {"NOT_FOUND", "BAD_REQUEST"}:
                raise ValueError(saved.get("reason") or "experiment_evidence_rejected")
        durable_experiment = self.evaluate_experiment(durable_experiment["experiment_id"])
        evaluation = self.evaluation.normalize(
            durable_experiment["evaluation"], run_id=run_id, project_id=project_id
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
            "EVIDENCE": durable_experiment["definition"],
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
            "experiment": {
                "experiment_id": durable_experiment["experiment_id"],
                "status": durable_experiment["status"],
                "decision": durable_experiment["decision"],
            },
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
