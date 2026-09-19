from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.strategy_intelligence import StrategyIntelligence
from src.strategy_intelligence_store import StrategyIntelligenceStore


class StrategyIntelligenceRuntime:
    def __init__(
        self,
        store: StrategyIntelligenceStore,
        engine: Optional[StrategyIntelligence] = None,
    ):
        self.store = store
        self.engine = engine or StrategyIntelligence()

    def rank(
        self,
        project_id: str,
        *,
        decision_context: Optional[Dict[str, Any]],
        candidates: List[Dict[str, Any]],
        evidence_sufficient: bool = True,
    ) -> Dict[str, Any]:
        analysis = self.engine.rank(
            project_id=project_id,
            decision_context=decision_context,
            candidates=candidates,
            evidence_sufficient=evidence_sufficient,
        )
        persistence = self.store.record(analysis)
        return {
            "analysis": analysis,
            "persistence": persistence,
            "governance_unchanged": True,
            "external_action_executed": False,
            "o43_memory_mutated": False,
        }
