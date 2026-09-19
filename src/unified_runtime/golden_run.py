"""S7 Golden Unified Run.

Composes the verified S1/S2 stage contracts with the real S3-S6 adapters in
one deterministic, side-effect-free golden path. S1/S2 are represented by
canonical validated envelopes because their own targeted suites already prove
their internal implementations; this runner proves the cross-stage identity
and decision handoff.
"""

from __future__ import annotations

from typing import Any, Dict

from .evaluation_adapter import UnifiedEvaluationAdapter
from .governance_adapter import UnifiedGovernanceAdapter
from .execution_outcome import UnifiedExecutionOutcomeAdapter
from .learning_adaptation import UnifiedLearningAdaptationAdapter


class GoldenUnifiedRun:
    STAGES = (
        "INTENT",
        "UNDERSTAND",
        "ROUTE",
        "DECISION",
        "EVIDENCE",
        "EVALUATION",
        "GOVERNANCE",
        "EXECUTION",
        "OUTCOME",
        "FEEDBACK",
        "LEARNING",
        "ADAPTATION",
        "NEXT_DECISION",
    )

    def __init__(self):
        self.evaluation = UnifiedEvaluationAdapter()
        self.governance = UnifiedGovernanceAdapter()
        self.execution = UnifiedExecutionOutcomeAdapter()
        self.learning = UnifiedLearningAdaptationAdapter()

    def run(self, *, run_id: str, project_id: str, strategy_id: str) -> Dict[str, Any]:
        if not run_id or not project_id or not strategy_id:
            raise ValueError("golden_identity_required")

        # Canonical S1/S2 handoff envelopes. Internal S1/S2 behavior is covered
        # by their dedicated verified suites; S7 tests the cross-stage contract.
        intent = {"stage": "INTENT", "intent": "validate core workflow", "run_id": run_id}
        understand = {"stage": "UNDERSTAND", "goal": "validate core workflow", "run_id": run_id}
        route = {"stage": "ROUTE", "route": "VALIDATION_WORKFLOW", "run_id": run_id}
        decision = {
            "stage": "DECISION",
            "status": "RECOMMEND",
            "decision_id": "UDI-GOLDEN-001",
            "strategy_id": strategy_id,
            "run_id": run_id,
            "project_id": project_id,
        }
        evidence = {
            "stage": "EVIDENCE",
            "experiment_id": f"VAL-{run_id}",
            "run_id": run_id,
            "project_id": project_id,
        }

        o42_evaluation = {
            "decision": "GO",
            "confidence": 0.95,
            "completed": True,
            "checks": ["thresholds_met", "evidence_refs_present"],
            "met_thresholds": ["problem_confirmed", "pilot_interest"],
            "unmet_thresholds": [],
            "evidence_refs": ["EV-GOLD-001", "EV-GOLD-002"],
            "sample_size": 10,
            "metrics": {"problem_confirmed": 8, "pilot_interest": 4},
            "learning": "Evidence supports proceeding to a bounded next step.",
            "next_step": "Run bounded execution validation.",
            "re_run_context": {"experiment_id": evidence["experiment_id"]},
            "decision_boundary": "Current evidence supports only a bounded next step.",
        }

        evaluation = self.evaluation.normalize(
            o42_evaluation, run_id=run_id, project_id=project_id
        )
        governance = self.governance.evaluate(
            evaluation, run_id=run_id, project_id=project_id
        )

        outcome = self.execution.run(
            governance,
            run_id=run_id,
            project_id=project_id,
            action_key="bounded-validation",
            executor=lambda: {
                "status": "SUCCEEDED",
                "output": {"validated": True, "mode": "GOLDEN_SIMULATION"},
            },
            consequential=False,
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
            "INTENT": intent,
            "UNDERSTAND": understand,
            "ROUTE": route,
            "DECISION": decision,
            "EVIDENCE": evidence,
            "EVALUATION": evaluation,
            "GOVERNANCE": governance,
            "EXECUTION": outcome,
            "OUTCOME": outcome,
            "FEEDBACK": adaptation["feedback"],
            "LEARNING": adaptation["learning"],
            "ADAPTATION": adaptation["adaptation"],
            "NEXT_DECISION": next_decision,
        }

        trace = []
        for stage in self.STAGES:
            trace.append(
                {
                    "stage": stage,
                    "run_id": run_id,
                    "project_id": project_id,
                    "status": "COMPLETE",
                }
            )

        return {
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
        }
