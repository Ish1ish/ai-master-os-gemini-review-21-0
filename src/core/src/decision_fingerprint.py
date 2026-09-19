from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterable, List


class DecisionFingerprint:
    """Deterministic, context-aware representation of a governed decision.

    The fingerprint separates stable decision context from learned outcome signals.
    Learned signals are reported on the fingerprint but are intentionally excluded
    from the base matching key so that the system can compare prior outcomes against
    the current candidate without circularly matching on the result it is trying to
    learn.
    """

    MATCH_FIELDS = (
        "action_types",
        "tools",
        "risk_class",
        "project_id",
        "tenant_id",
        "evidence_pattern",
    )

    @staticmethod
    def _norm(value: Any, default: str = "UNKNOWN") -> str:
        value = str(value or "").strip()
        return value.upper() if value else default

    @classmethod
    def _actions(cls, prediction: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw = prediction.get("actions")
        if not isinstance(raw, list):
            return []
        return [item for item in raw if isinstance(item, dict)]

    @classmethod
    def _action_types(cls, actions: Iterable[Dict[str, Any]]) -> List[str]:
        values = set()
        for action in actions:
            value = action.get("action_type", action.get("type", action.get("action")))
            if value:
                values.add(cls._norm(value))
        return sorted(values) or ["NONE"]

    @classmethod
    def _tools(cls, actions: Iterable[Dict[str, Any]]) -> List[str]:
        values = set()
        for action in actions:
            value = action.get("tool", action.get("tool_name", action.get("provider")))
            if value:
                values.add(cls._norm(value))
        return sorted(values) or ["NONE"]

    @classmethod
    def _evidence_pattern(cls, prediction: Dict[str, Any]) -> str:
        evidence = prediction.get("evidence")
        if evidence is None:
            evidence = prediction.get("evidence_items")
        if evidence is None:
            evidence = prediction.get("sources")
        if not evidence:
            return "NO_EVIDENCE"
        if isinstance(evidence, dict):
            evidence = list(evidence.values())
        if not isinstance(evidence, list):
            evidence = [evidence]
        kinds = set()
        for item in evidence:
            if isinstance(item, dict):
                source = item.get("source", item.get("type", item.get("kind", "LOCAL")))
            else:
                source = "LOCAL"
            s = cls._norm(source)
            if "TAVILY" in s or "WEB" in s or "EXTERNAL" in s or "REMOTE" in s:
                kinds.add("EXTERNAL")
            else:
                kinds.add("LOCAL")
        if kinds == {"LOCAL"}:
            return "LOCAL_EVIDENCE"
        if kinds == {"EXTERNAL"}:
            return "EXTERNAL_EVIDENCE"
        return "MIXED_EVIDENCE"

    @staticmethod
    def accuracy_band(accuracy: Any, sample_count: int) -> str:
        if sample_count < 1 or accuracy is None:
            return "UNKNOWN"
        value = float(accuracy)
        if value >= 0.8:
            return "HIGH"
        if value >= 0.5:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def drift_band(scores: Iterable[float]) -> str:
        values = [float(v) for v in scores]
        if len(values) < 2:
            return "UNKNOWN"
        midpoint = max(1, len(values) // 2)
        early = sum(values[:midpoint]) / midpoint
        late_values = values[midpoint:]
        late = sum(late_values) / len(late_values)
        delta = round(late - early, 3)
        if delta <= -0.5:
            return "DETERIORATING"
        if delta >= 0.5:
            return "IMPROVING"
        return "STABLE"

    @classmethod
    def build(
        cls,
        *,
        prediction: Dict[str, Any],
        project_id: str,
        tenant_id: str | None = None,
        historical_accuracy: Any = None,
        sample_count: int = 0,
        recent_scores: Iterable[float] = (),
    ) -> Dict[str, Any]:
        actions = cls._actions(prediction)
        decision = cls._norm(prediction.get("decision"), "BLOCK")
        risk = cls._norm(prediction.get("risk"), "HIGH")
        payload = {
            "action_types": cls._action_types(actions),
            "tools": cls._tools(actions),
            "risk_class": risk,
            "project_id": str(project_id or "UNKNOWN"),
            "tenant_id": str(tenant_id or prediction.get("tenant_id") or "DEFAULT"),
            "evidence_pattern": cls._evidence_pattern(prediction),
            "historical_accuracy": cls.accuracy_band(historical_accuracy, int(sample_count)),
            "calibration_drift": cls.drift_band(recent_scores),
            "decision": decision,
        }
        base = {field: payload[field] for field in cls.MATCH_FIELDS}
        raw = json.dumps(base, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        payload["fingerprint"] = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20].upper()
        payload["match_key"] = base
        return payload

    @classmethod
    def from_record(cls, record: Dict[str, Any]) -> Dict[str, Any]:
        prediction = record.get("prediction") or {}
        project_id = record.get("project_id") or prediction.get("project_id") or "UNKNOWN"
        learning = record.get("learning") or {}
        score = learning.get("score")
        accuracy = 1.0 if learning.get("calibration") == "EXACT_MATCH" else 0.0 if learning else None
        return cls.build(
            prediction=prediction,
            project_id=project_id,
            tenant_id=prediction.get("tenant_id") or record.get("tenant_id"),
            historical_accuracy=accuracy,
            sample_count=1 if learning else 0,
            recent_scores=[score] if score is not None else [],
        )

    @classmethod
    def matches(cls, candidate: Dict[str, Any], prior: Dict[str, Any]) -> bool:
        return all(candidate.get(field) == prior.get(field) for field in cls.MATCH_FIELDS)
