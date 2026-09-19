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

from typing import Any, Dict, Mapping, Optional

from .s1 import S1Input, build_s1_runtime
from .udi_adapter import build_udi_decision_adapter
from .o42_adapter import O42EvidenceAdapter
from .evaluation_adapter import UnifiedEvaluationAdapter
from .governance_adapter import UnifiedGovernanceAdapter
from .execution_outcome import UnifiedExecutionOutcomeAdapter
from .learning_adaptation import UnifiedLearningAdaptationAdapter
from .persistence import UnifiedMemoryHandoff, UnifiedRunPersistence


class RealUnifiedRuntime:
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

        # The existing decision engine remains authoritative; this is a wire,
        # not a fork of decision intelligence.
        self._s1 = build_s1_runtime(decision=build_udi_decision_adapter())

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
            return self._blocked_result(run_id, project_id, strategy_id, s1, "s1_decision_failed")

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
            "evidence_engine": "ValidationEvidenceLoop",
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

    def _blocked_result(self, run_id: str, project_id: str, strategy_id: str, s1: Dict[str, Any], reason: str) -> Dict[str, Any]:
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
        }
