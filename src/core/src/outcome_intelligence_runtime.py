from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from src.execution_observability import ExecutionObservabilityStore
from src.learning_signal_adapter import to_o43_lesson
from src.outcome_intelligence import OutcomeIntelligence
from src.outcome_intelligence_store import OutcomeIntelligenceStore


class OutcomeIntelligenceRuntime:
    """Read v1.4 trace evidence, persist v1.5 assessment, emit bounded O43 lesson."""

    def __init__(
        self,
        observability_store: ExecutionObservabilityStore,
        assessment_store: OutcomeIntelligenceStore,
        engine: Optional[OutcomeIntelligence] = None,
    ):
        self.observability_store = observability_store
        self.assessment_store = assessment_store
        self.engine = engine or OutcomeIntelligence()

    def assess_trace(
        self,
        trace_id: str,
        *,
        target_status: str,
        evidence_refs: Optional[Sequence[str]] = None,
        confidence: str = "medium",
        attribution_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        trace = self.observability_store.trace(trace_id)
        assessment = self.engine.assess(
            trace=trace,
            target_status=target_status,
            evidence_refs=evidence_refs,
            confidence=confidence,
            attribution_hint=attribution_hint,
        )
        persisted = self.assessment_store.record(assessment)
        lesson = to_o43_lesson(assessment)

        return {
            "assessment": assessment,
            "persistence": persisted,
            "o43_lesson": lesson,
            "o43_handoff_ready": lesson is not None,
        }
