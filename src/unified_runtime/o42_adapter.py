"""S2 bridge to the existing O42 ValidationEvidenceLoop.

The existing O42 implementation remains authoritative for experiment definition
normalization and deterministic evidence evaluation. This bridge adds only the
Unified Runtime boundary around it.
"""

from __future__ import annotations

from typing import Any, Dict

from core.src.evidence_loop import ValidationEvidenceLoop, build_experiment_from_decision_surface


class O42EvidenceAdapter:
    def __init__(self, evaluator: ValidationEvidenceLoop | None = None):
        self.engine = evaluator or ValidationEvidenceLoop()

    def build_experiment(
        self,
        decision_surface: Dict[str, Any],
        *,
        run_id: str,
        project_id: str,
        language: str = "en",
    ) -> Dict[str, Any]:
        return build_experiment_from_decision_surface(
            decision_surface,
            run_id=run_id,
            project_id=project_id,
            language=language,
        )

    def evaluate(
        self,
        definition: Dict[str, Any],
        evidence: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        return self.engine.evaluate(definition, evidence)

    def evaluate_decision_surface(
        self,
        decision_surface: Dict[str, Any],
        *,
        run_id: str,
        project_id: str,
        evidence: Dict[str, Any] | None = None,
        language: str = "en",
    ) -> Dict[str, Any]:
        definition = self.build_experiment(
            decision_surface,
            run_id=run_id,
            project_id=project_id,
            language=language,
        )
        result = self.evaluate(definition, evidence)
        return {
            "experiment": definition,
            "evaluation": result,
            "run_id": run_id,
            "project_id": project_id,
        }
