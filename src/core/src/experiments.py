from __future__ import annotations

from typing import Any, Dict, Optional

from .evidence_loop import ValidationEvidenceLoop, build_experiment_from_decision_surface
from .experiment_store import ExperimentStore
from .learning_loop import LearningDecisionLoop


class ExperimentService:
    def __init__(self, store: ExperimentStore, jobs, memory_runtime=None):
        self.store = store
        self.jobs = jobs
        self.memory_runtime = memory_runtime
        self.loop = ValidationEvidenceLoop()
        self.learning = LearningDecisionLoop(store, getattr(memory_runtime, "store", None))

    def create_from_run(self, run_id: str) -> Dict[str, Any]:
        job = self.jobs.get(run_id)
        if not job:
            return {"status": "NOT_FOUND", "run_id": run_id}
        result = job.get("result") or {}
        surface = result.get("decision_surface") or {}
        if not surface:
            return {"status": "CONFLICT", "reason": "run_has_no_decision_surface", "run_id": run_id}
        definition = build_experiment_from_decision_surface(surface, run_id, job["project_id"], job.get("language", "en"))
        existing = self.store.list(project_id=job["project_id"], limit=200)
        for item in existing:
            if item.get("run_id") == run_id:
                return item
        return self.store.create(definition, job["project_id"], run_id=run_id)

    def get(self, experiment_id: str) -> Dict[str, Any]:
        return self.store.get(experiment_id) or {"status": "NOT_FOUND", "experiment_id": experiment_id}

    def list(self, project_id: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        return {"status": "OK", "experiments": self.store.list(project_id=project_id, limit=limit)}

    def record_evidence(self, experiment_id: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
        exp = self.store.get(experiment_id)
        if not exp:
            return {"status": "NOT_FOUND", "experiment_id": experiment_id}
        sample = evidence.get("sample_size")
        if sample is None:
            return {"status": "BAD_REQUEST", "reason": "sample_size_required", "experiment_id": experiment_id}
        if int(sample) < 0:
            return {"status": "BAD_REQUEST", "reason": "sample_size_invalid", "experiment_id": experiment_id}
        metrics = evidence.get("metrics") or {}
        refs = evidence.get("evidence_refs") or []
        normalized = {
            "sample_size": int(sample),
            "metrics": dict(metrics),
            "evidence_refs": [str(x).strip() for x in refs if str(x).strip()],
            "notes": str(evidence.get("notes") or "").strip(),
            "observations": evidence.get("observations") or [],
        }
        return self.store.save_evidence(experiment_id, normalized)

    def get_learning_context(self, project_id: str, current_experiment_id: str | None = None) -> Dict[str, Any]:
        return self.learning.build_next_cycle_context(project_id, current_experiment_id=current_experiment_id)

    def evaluate(self, experiment_id: str) -> Dict[str, Any]:
        exp = self.store.get(experiment_id)
        if not exp:
            return {"status": "NOT_FOUND", "experiment_id": experiment_id}
        evaluation = self.loop.evaluate(exp["definition"], exp.get("evidence") or {})
        updated = self.store.save_evaluation(experiment_id, evaluation)
        if updated.get("evaluation") and updated["evaluation"].get("decision") in {"GO", "REFINE", "NO-GO"} and self.memory_runtime is not None:
            lesson = {
                "run_id": f"EXP-{experiment_id}",
                "project_id": updated["project_id"],
                "experiment": {
                    "experiment_id": experiment_id,
                    "version": "v1.0",
                    "status": "concluded",
                    "learning": updated["evaluation"].get("learning") or updated["evaluation"].get("summary") or "",
                    "confidence": updated["evaluation"].get("confidence") or "medium",
                    "source_refs": updated["evaluation"].get("evidence_refs") or [],
                },
                "decision": {
                    "decision_id": f"DEC-{experiment_id}",
                    "version": "v1.0",
                    "summary": updated["evaluation"].get("summary") or "",
                    "confidence": updated["evaluation"].get("confidence") or "medium",
                    "source_refs": updated["evaluation"].get("evidence_refs") or [],
                },
                "learning": updated["evaluation"].get("learning") or "",
                "source_refs": updated["evaluation"].get("evidence_refs") or [],
            }
            memory = self.memory_runtime.process_run(lesson, {"status": "PASS"})
            updated["memory"] = memory
            updated["next_cycle_context"] = self.learning.build_next_cycle_context(updated["project_id"], current_experiment_id=experiment_id)
        return updated
