from __future__ import annotations

from typing import Any, Dict, Optional

from src.advanced_outcome_analysis import AdvancedOutcomeAnalysis
from src.advanced_outcome_analysis_store import AdvancedOutcomeAnalysisStore
from src.outcome_intelligence_store import OutcomeIntelligenceStore


class AdvancedOutcomeAnalysisRuntime:
    """Read v1.5 assessments, analyze patterns, persist the aggregate, stay advisory."""

    def __init__(
        self,
        assessment_store: OutcomeIntelligenceStore,
        analysis_store: AdvancedOutcomeAnalysisStore,
        analyzer: Optional[AdvancedOutcomeAnalysis] = None,
    ):
        self.assessment_store = assessment_store
        self.analysis_store = analysis_store
        self.analyzer = analyzer or AdvancedOutcomeAnalysis()

    def analyze_project(
        self,
        project_id: str,
        *,
        limit: int = 20,
        window_size: int = 20,
        minimum_sample_size: int = 3,
    ) -> Dict[str, Any]:
        assessments = self.assessment_store.list_by_project(project_id, limit=limit)
        analysis = self.analyzer.analyze(
            project_id=project_id,
            assessments=assessments,
            window_size=window_size,
            minimum_sample_size=minimum_sample_size,
        )
        persistence = self.analysis_store.record(analysis)
        return {
            "analysis": analysis,
            "persistence": persistence,
            "advisory_only": True,
            "governance_unchanged": True,
            "external_action_executed": False,
            "o43_memory_mutated": False,
        }
