from __future__ import annotations

from typing import Any, Dict, List


DECISIONS = {"GO", "REFINE", "NO-GO"}


class LearningDecisionLoop:
    """Build bounded learning context from concluded experiments and durable memory.

    O43 intentionally remains deterministic: it does not let the model rewrite history.
    It ranks prior experiment lessons and emits a compact, traceable context package
    for the next decision cycle.
    """

    def __init__(self, experiment_store, memory_store=None):
        self.experiment_store = experiment_store
        self.memory_store = memory_store

    def build_project_context(self, project_id: str, limit: int = 20) -> Dict[str, Any]:
        experiments = self.experiment_store.list(project_id=project_id, limit=limit)
        concluded = [e for e in experiments if e.get("decision") in DECISIONS]
        latest = concluded[:]
        lessons: List[Dict[str, Any]] = []
        for exp in latest:
            evaluation = exp.get("evaluation") or {}
            lesson = {
                "experiment_id": exp.get("experiment_id"),
                "decision": exp.get("decision"),
                "confidence": evaluation.get("confidence") or "medium",
                "summary": evaluation.get("summary") or "",
                "learning": evaluation.get("learning") or "",
                "evidence_refs": list(evaluation.get("evidence_refs") or []),
                "sample_size": evaluation.get("sample_size", (exp.get("evidence") or {}).get("sample_size", 0)),
                "metrics": dict(evaluation.get("metrics") or (exp.get("evidence") or {}).get("metrics") or {}),
                "next_step": evaluation.get("next_step") or "",
                "re_run_context": dict(evaluation.get("re_run_context") or {}),
                "created_at": exp.get("updated_at") or exp.get("created_at"),
            }
            lessons.append(lesson)

        memory_lessons = []
        if self.memory_store is not None and hasattr(self.memory_store, "list_by_project"):
            for obj in self.memory_store.list_by_project(project_id, limit=100):
                if obj.get("object_type") == "Lesson":
                    memory_lessons.append({
                        "lesson_id": obj.get("object_id"),
                        "summary": obj.get("summary") or "",
                        "confidence": obj.get("confidence") or "medium",
                        "source_refs": list(obj.get("source_refs") or []),
                        "status": obj.get("status") or "active",
                    })
        stop_signals = [x for x in lessons if x["decision"] == "NO-GO"]
        refine_signals = [x for x in lessons if x["decision"] == "REFINE"]
        support_signals = [x for x in lessons if x["decision"] == "GO"]
        return {
            "status": "READY" if lessons else "EMPTY",
            "project_id": project_id,
            "experiment_count": len(experiments),
            "concluded_count": len(concluded),
            "lessons": lessons,
            "durable_memory_lessons": memory_lessons[:10],
            "routing_guidance": self._routing_guidance(support_signals, refine_signals, stop_signals),
            "decision_boundary": "Prior experiment outcomes are evidence for the next decision cycle, not proof that future outcomes will match.",
        }

    def _routing_guidance(self, support: List[Dict[str, Any]], refine: List[Dict[str, Any]], stop: List[Dict[str, Any]]) -> Dict[str, Any]:
        if stop:
            return {
                "preferred_action": "ROUTE_TO_NEXT_HYPOTHESIS",
                "reason": "A prior experiment produced a configured NO-GO; do not repeat the same hypothesis unchanged.",
                "blocked_experiment_ids": [x["experiment_id"] for x in stop],
            }
        if refine:
            return {
                "preferred_action": "REFINE_BEFORE_REBUILD",
                "reason": "Prior evidence missed one or more success thresholds; change one material variable before another run.",
                "refine_experiment_ids": [x["experiment_id"] for x in refine],
            }
        if support:
            return {
                "preferred_action": "BOUNDED_NEXT_STEP",
                "reason": "Prior evidence met success thresholds; proceed with the smallest bounded next test.",
                "supported_experiment_ids": [x["experiment_id"] for x in support],
            }
        return {
            "preferred_action": "COLLECT_INITIAL_EVIDENCE",
            "reason": "No concluded experiment exists for this project yet.",
        }

    def build_next_cycle_context(self, project_id: str, current_experiment_id: str | None = None) -> Dict[str, Any]:
        context = self.build_project_context(project_id)
        lessons = [x for x in context["lessons"] if x["experiment_id"] != current_experiment_id]
        context["lessons"] = lessons
        context["context_id"] = f"CTX-{project_id}-{len(lessons):02d}"
        context["retrieval_policy"] = {
            "max_lessons": min(len(lessons), 5),
            "prioritize": ["NO-GO", "REFINE", "GO"],
            "require_evidence_refs": True,
            "exclude_inconclusive": True,
        }
        return context
