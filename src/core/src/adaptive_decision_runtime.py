from __future__ import annotations

from typing import Any, Dict, Optional

from src.adaptive_decision_context import AdaptiveDecisionContext
from src.adaptive_decision_context_store import AdaptiveDecisionContextStore


class AdaptiveDecisionRuntime:
    """Consumes v1.6 analysis and emits a bounded v1.7 decision context."""

    def __init__(
        self,
        context_store: AdaptiveDecisionContextStore,
        adapter: Optional[AdaptiveDecisionContext] = None,
    ):
        self.context_store = context_store
        self.adapter = adapter or AdaptiveDecisionContext()

    def build_context(
        self,
        project_id: str,
        *,
        analysis: Optional[Dict[str, Any]],
        candidate_decision: str,
        governance_required: bool = True,
        evidence_sufficient: bool = True,
    ) -> Dict[str, Any]:
        context = self.adapter.build(
            project_id=project_id,
            analysis=analysis,
            candidate_decision=candidate_decision,
            governance_required=governance_required,
            evidence_sufficient=evidence_sufficient,
        )
        persistence = self.context_store.record(context)
        return {
            "context": context,
            "persistence": persistence,
            "governance_unchanged": True,
            "external_action_executed": False,
            "o43_memory_mutated": False,
        }
