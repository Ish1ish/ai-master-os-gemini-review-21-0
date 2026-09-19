from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple


ALLOWED_DECISIONS = {"GO", "REFINE", "NO-GO", "INCONCLUSIVE"}


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Threshold:
    metric: str
    operator: str
    value: float
    hard_failure_below: float | None = None


class ValidationEvidenceLoop:
    """Deterministic O42 evaluator: hypothesis -> evidence -> decision -> learning."""

    def normalize_definition(self, experiment: Dict[str, Any]) -> Dict[str, Any]:
        definition = dict(experiment or {})
        definition.setdefault("status", "READY")
        definition.setdefault("sample_size", 0)
        definition.setdefault("measure", [])
        definition.setdefault("timebox_days", None)
        definition.setdefault("external_action_required", False)
        definition.setdefault("decision_rule", "GO when success thresholds are met; otherwise REFINE.")

        raw = definition.get("thresholds_machine") or definition.get("success_threshold") or {}
        machine: Dict[str, Dict[str, Any]] = {}
        for metric, spec in raw.items():
            if isinstance(spec, dict):
                machine[str(metric)] = {
                    "operator": spec.get("operator", ">="),
                    "value": _float(spec.get("value", 0)),
                    "description": spec.get("description") or spec.get("text", ""),
                }
            else:
                text = str(spec)
                # Legacy O41 threshold strings. Map the known validation experiment into machine rules.
                if "6/10" in text:
                    machine[str(metric)] = {"operator": ">=", "value": 6, "description": text}
                elif "3/10" in text:
                    machine[str(metric)] = {"operator": ">=", "value": 3, "description": text}
                else:
                    machine[str(metric)] = {"operator": ">=", "value": 1, "description": text}
        definition["thresholds_machine"] = machine
        definition.setdefault("no_go_thresholds", {})
        return definition

    def evaluate(self, definition: Dict[str, Any], evidence: Dict[str, Any] | None) -> Dict[str, Any]:
        definition = self.normalize_definition(definition)
        evidence = dict(evidence or {})
        sample_size = _int(evidence.get("sample_size", definition.get("sample_size", 0)))
        metrics = evidence.get("metrics") or {}
        refs = [str(r).strip() for r in (evidence.get("evidence_refs") or []) if str(r).strip()]
        thresholds = definition.get("thresholds_machine") or {}

        if sample_size <= 0:
            return self._result("INCONCLUSIVE", "No measured sample was recorded yet.", 0.0, [], [], refs, evidence, definition)

        unmet: List[Dict[str, Any]] = []
        met: List[Dict[str, Any]] = []
        checks: List[Dict[str, Any]] = []
        for metric, rule in thresholds.items():
            observed = _float(metrics.get(metric), 0)
            target = _float(rule.get("value"), 0)
            op = rule.get("operator", ">=")
            passed = self._compare(observed, op, target)
            item = {"metric": metric, "observed": observed, "operator": op, "target": target, "pass": passed}
            checks.append(item)
            (met if passed else unmet).append(item)

        complete = sample_size >= _int(definition.get("sample_size", 0)) if _int(definition.get("sample_size", 0)) else bool(metrics)
        if not refs:
            return self._result(
                "INCONCLUSIVE",
                "Measured results exist, but evidence references are missing; do not treat this as decision-grade evidence.",
                "low",
                met,
                unmet,
                refs,
                evidence,
                definition,
                checks=checks,
                complete=complete,
            )

        no_go = self._no_go_trigger(definition.get("no_go_thresholds") or {}, metrics) if complete else None
        if no_go:
            decision = "NO-GO"
            summary = no_go
        elif complete and not unmet:
            decision = "GO"
            summary = "All success thresholds were met with recorded evidence."
        elif complete and unmet:
            decision = "REFINE"
            summary = "The experiment reached its planned sample, but one or more success thresholds were missed; refine the problem, segment, or offer and re-test."
        else:
            decision = "INCONCLUSIVE"
            summary = "Evidence is partially recorded; complete the planned sample before making a GO/REFINE/NO-GO decision."

        confidence = self._confidence(decision, complete, len(refs), sample_size, len(thresholds))
        learning = self._learning_summary(decision, met, unmet, metrics)
        return self._result(decision, summary, confidence, met, unmet, refs, evidence, definition, checks=checks, complete=complete, learning=learning)

    @staticmethod
    def _compare(observed: float, operator: str, target: float) -> bool:
        return {
            ">=": observed >= target,
            ">": observed > target,
            "<=": observed <= target,
            "<": observed < target,
            "==": observed == target,
        }.get(operator, False)

    @staticmethod
    def _no_go_trigger(rules: Dict[str, Any], metrics: Dict[str, Any]) -> str | None:
        for metric, rule in rules.items():
            if not isinstance(rule, dict):
                continue
            observed = _float(metrics.get(metric), 0)
            target = _float(rule.get("value"), 0)
            operator = rule.get("operator", "<")
            if ValidationEvidenceLoop._compare(observed, operator, target):
                return str(rule.get("reason") or f"No-go threshold triggered for {metric}.")
        return None

    @staticmethod
    def _confidence(decision: str, complete: bool, refs: int, sample: int, threshold_count: int) -> str:
        if decision == "INCONCLUSIVE":
            return "low" if not complete or refs < 1 else "medium"
        if complete and refs >= max(2, threshold_count) and sample >= 10:
            return "high"
        return "medium"

    @staticmethod
    def _learning_summary(decision: str, met: List[Dict[str, Any]], unmet: List[Dict[str, Any]], metrics: Dict[str, Any]) -> str:
        if decision == "GO":
            return "The measured evidence supports moving the validated hypothesis forward; next step is a bounded build or paid pilot."
        if decision == "REFINE":
            failed = ", ".join(x["metric"] for x in unmet) or "the success thresholds"
            return f"The experiment did not fully validate the hypothesis. Weakest signals: {failed}. Refine the segment/problem/offer and re-test."
        if decision == "NO-GO":
            return "The measured evidence crossed a configured no-go condition; stop this direction for now and preserve the lesson for future routing."
        return "There is not enough decision-grade evidence yet; complete the experiment before updating the business decision."

    def _result(self, decision, summary, confidence, met, unmet, refs, evidence, definition, checks=None, complete=False, learning=None):
        return {
            "status": "EVALUATED",
            "decision": decision,
            "summary": summary,
            "confidence": confidence,
            "completed": bool(complete),
            "checks": checks or [],
            "met_thresholds": met,
            "unmet_thresholds": unmet,
            "evidence_refs": refs,
            "sample_size": _int(evidence.get("sample_size", definition.get("sample_size", 0))),
            "metrics": dict(evidence.get("metrics") or {}),
            "learning": learning or "",
            "next_step": self._next_step(decision),
            "re_run_context": self._rerun_context(decision, definition, learning or summary),
            "decision_boundary": "Decision is an evidence-based experiment outcome, not proof of long-term business success.",
        }

    @staticmethod
    def _rerun_context(decision: str, definition: Dict[str, Any], learning: str) -> Dict[str, Any]:
        return {
            "recommended": decision in {"REFINE", "INCONCLUSIVE"},
            "reason": learning,
            "experiment_id": definition.get("experiment_id"),
            "instruction": (
                "Change one material variable and re-run the validation experiment."
                if decision == "REFINE" else
                "Collect the missing decision-grade evidence, then re-run evaluation."
                if decision == "INCONCLUSIVE" else
                "Re-run only when new evidence could materially change the business decision."
            ),
        }

    @staticmethod
    def _next_step(decision: str) -> str:
        return {
            "GO": "Run the smallest bounded pilot or MVP test that delivers the promised outcome.",
            "REFINE": "Change one material variable in the problem, segment, or offer and re-run the experiment.",
            "NO-GO": "Stop this direction, record the lesson, and route to the next ranked hypothesis.",
            "INCONCLUSIVE": "Collect the remaining planned evidence before making a directional decision.",
        }[decision]



def build_experiment_from_decision_surface(surface: Dict[str, Any], run_id: str, project_id: str, language: str = "en") -> Dict[str, Any]:
    exp = dict(surface.get("validation_experiment") or {})
    if not exp:
        raise ValueError("decision_surface_has_no_validation_experiment")
    exp.setdefault("experiment_id", f"VAL-{run_id}")
    exp["run_id"] = run_id
    exp["project_id"] = project_id
    exp["hypothesis"] = exp.get("hypothesis") or "The target customer experiences the stated problem strongly enough to justify a focused solution."
    exp["language"] = language
    exp["decision_context"] = {
        "recommendation": surface.get("recommendation"),
        "customer": surface.get("customer"),
        "problem": surface.get("problem"),
        "desired_outcome": surface.get("desired_outcome"),
        "opportunity_score": surface.get("opportunity_score"),
        "strategy_score": surface.get("strategy_score"),
        "confidence": surface.get("confidence"),
        "evidence_boundary": surface.get("evidence_boundary"),
    }
    return ValidationEvidenceLoop().normalize_definition(exp)
