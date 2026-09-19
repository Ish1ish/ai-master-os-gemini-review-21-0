from __future__ import annotations

import hashlib
import json
from statistics import pstdev
from typing import Any, Dict, Iterable, List, Optional


class ProductionIntelligence:
    """Evidence-bound operational intelligence for cost, latency, reliability, and resources.

    v0.9 is advisory-first. It does not execute actions or weaken governance.
    """

    RELIABILITY_BANDS = {"UNKNOWN", "WEAK", "MODERATE", "STRONG"}
    PRESSURE_BANDS = {"UNKNOWN", "NORMAL", "ELEVATED", "CRITICAL"}

    @staticmethod
    def _canonical(payload: Dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def recommendation_id(cls, project_id: str, context: Dict[str, Any], recommendation: Dict[str, Any]) -> str:
        raw = {"project_id": str(project_id), "context": context, "recommendation": recommendation}
        digest = hashlib.sha256(cls._canonical(raw).encode("utf-8")).hexdigest()[:20].upper()
        return f"PI-{digest}"

    @staticmethod
    def _number(value: Any) -> Optional[float]:
        if isinstance(value, bool) or value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def normalize_observation(cls, observation: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(observation, dict):
            return {"status": "REJECTED", "reasons": ["observation_must_be_object"]}
        required = ("provider", "tool", "observed_at")
        reasons = [f"missing_{key}" for key in required if not str(observation.get(key) or "").strip()]
        cost = cls._number(observation.get("cost_usd"))
        latency = cls._number(observation.get("latency_ms"))
        success = cls._number(observation.get("success_rate"))
        cpu = cls._number(observation.get("cpu_pct"))
        memory = cls._number(observation.get("memory_pct"))
        if cost is not None and cost < 0:
            reasons.append("cost_must_be_non_negative")
        if latency is not None and latency < 0:
            reasons.append("latency_must_be_non_negative")
        if success is not None and not 0.0 <= success <= 1.0:
            reasons.append("success_rate_out_of_range")
        for name, value in (("cpu_pct", cpu), ("memory_pct", memory)):
            if value is not None and not 0.0 <= value <= 100.0:
                reasons.append(f"{name}_out_of_range")
        if reasons:
            return {"status": "REJECTED", "reasons": reasons}
        reliability = cls.reliability_band(success_rate=success, sample_count=int(observation.get("sample_count") or 0))
        freshness = str(observation.get("freshness") or "UNKNOWN").upper()
        return {
            "status": "NORMALIZED",
            "provider": str(observation["provider"]),
            "tool": str(observation["tool"]),
            "observed_at": str(observation["observed_at"]),
            "cost_usd": None if cost is None else round(cost, 6),
            "latency_ms": None if latency is None else round(latency, 3),
            "success_rate": None if success is None else round(success, 6),
            "sample_count": max(0, int(observation.get("sample_count") or 0)),
            "cpu_pct": None if cpu is None else round(cpu, 3),
            "memory_pct": None if memory is None else round(memory, 3),
            "reliability_band": reliability,
            "freshness": freshness,
            "evidence_refs": list(observation.get("evidence_refs") or []),
        }

    @staticmethod
    def reliability_band(*, success_rate: Optional[float], sample_count: int) -> str:
        n = max(0, int(sample_count))
        if success_rate is None or n == 0:
            return "UNKNOWN"
        if n >= 50 and success_rate >= 0.99:
            return "STRONG"
        if n >= 10 and success_rate >= 0.95:
            return "MODERATE"
        return "WEAK"

    @classmethod
    def resource_pressure(cls, *, cpu_pct: Optional[float], memory_pct: Optional[float]) -> Dict[str, Any]:
        if cpu_pct is None and memory_pct is None:
            return {"band": "UNKNOWN", "reasons": ["missing_resource_telemetry"]}
        values = [v for v in (cpu_pct, memory_pct) if v is not None]
        peak = max(values)
        if peak >= 95:
            band = "CRITICAL"
        elif peak >= 85:
            band = "ELEVATED"
        else:
            band = "NORMAL"
        reasons: List[str] = []
        if cpu_pct is not None and cpu_pct >= 85:
            reasons.append("high_cpu_pressure")
        if memory_pct is not None and memory_pct >= 85:
            reasons.append("high_memory_pressure")
        return {"band": band, "reasons": reasons}

    @staticmethod
    def latency_posture(latency_ms: Optional[float], threshold_ms: float) -> str:
        if latency_ms is None:
            return "UNKNOWN"
        if latency_ms > threshold_ms:
            return "SLOW"
        return "NORMAL"

    @classmethod
    def assess(cls, observations: Iterable[Dict[str, Any]], *, max_latency_ms: float, max_cost_usd: float) -> Dict[str, Any]:
        normalized: List[Dict[str, Any]] = []
        rejected = 0
        for item in observations:
            out = cls.normalize_observation(item)
            if out.get("status") == "NORMALIZED":
                normalized.append(out)
            else:
                rejected += 1
        costs = [o["cost_usd"] for o in normalized if o["cost_usd"] is not None]
        latencies = [o["latency_ms"] for o in normalized if o["latency_ms"] is not None]
        success = [o["success_rate"] for o in normalized if o["success_rate"] is not None]
        resource = cls.resource_pressure(
            cpu_pct=max((o["cpu_pct"] for o in normalized if o["cpu_pct"] is not None), default=None),
            memory_pct=max((o["memory_pct"] for o in normalized if o["memory_pct"] is not None), default=None),
        )
        return {
            "status": "ASSESSED",
            "observation_count": len(normalized),
            "rejected_count": rejected,
            "avg_cost_usd": None if not costs else round(sum(costs) / len(costs), 6),
            "avg_latency_ms": None if not latencies else round(sum(latencies) / len(latencies), 3),
            "latency_posture": cls.latency_posture(None if not latencies else sum(latencies) / len(latencies), max_latency_ms),
            "cost_posture": "OVER_BUDGET" if costs and sum(costs) / len(costs) > max_cost_usd else ("UNKNOWN" if not costs else "WITHIN_BUDGET"),
            "success_rate": None if not success else round(sum(success) / len(success), 6),
            "reliability_bands": sorted({o["reliability_band"] for o in normalized}),
            "resource_pressure": resource,
            "latency_stddev_ms": None if len(latencies) < 2 else round(pstdev(latencies), 3),
            "telemetry_boundary": "Missing telemetry is unknown evidence; it never implies healthy production behavior.",
        }

    @classmethod
    def recommend(cls, *, project_id: str, context: Dict[str, Any], assessment: Dict[str, Any], candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        if assessment.get("status") != "ASSESSED":
            return {"status": "REJECTED", "reason": "assessment_required"}
        safe_candidates = []
        for candidate in candidates:
            if not isinstance(candidate, dict) or not candidate.get("provider") or not candidate.get("tool"):
                continue
            safe_candidates.append(candidate)
        ranked = sorted(
            safe_candidates,
            key=lambda c: (
                float(c.get("cost_usd", 10**9)),
                float(c.get("latency_ms", 10**9)),
                -float(c.get("success_rate", 0.0)),
                str(c.get("provider")),
                str(c.get("tool")),
            ),
        )
        top = ranked[0] if ranked else None
        pressure = (assessment.get("resource_pressure") or {}).get("band")
        caution = pressure in {"ELEVATED", "CRITICAL"} or assessment.get("latency_posture") == "SLOW" or "WEAK" in (assessment.get("reliability_bands") or [])
        recommendation = {
            "status": "ADVISORY",
            "project_id": str(project_id),
            "action": "RECOMMEND_PROVIDER_OR_TOOL" if top else "HOLD_AND_COLLECT_TELEMETRY",
            "target": None if top is None else {"provider": top["provider"], "tool": top["tool"]},
            "reason": "resource_aware_bounded_recommendation" if top else "insufficient_usable_candidates",
            "caution": "ELEVATED" if caution else "NORMAL",
            "requires_governance": True,
            "external_action_executed": False,
            "governance_authority": "POLICY_AND_GOVERNANCE_REMAIN_AUTHORITATIVE",
        }
        recommendation["recommendation_id"] = cls.recommendation_id(project_id, context, recommendation)
        return recommendation
