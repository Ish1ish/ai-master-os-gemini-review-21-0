from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterable, List, Optional


class UnifiedDecisionIntelligence:
    """Phase 2 integrated intelligence: rank bounded routes using evidence already
    produced by contextual calibration and production intelligence.

    Advisory-only. It never executes actions or bypasses governance.
    """

    ROUTE_STATUSES = {"RECOMMEND", "REFINE", "HOLD"}

    @staticmethod
    def _canonical(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def plan_id(cls, project_id: str, context: Dict[str, Any], candidates: List[Dict[str, Any]]) -> str:
        raw = {"project_id": str(project_id), "context": context, "candidates": candidates}
        digest = hashlib.sha256(cls._canonical(raw).encode("utf-8")).hexdigest()[:24].upper()
        return f"UDI-{digest}"

    @staticmethod
    def _safe_float(value: Any, default: float) -> float:
        if isinstance(value, bool):
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _uncertainty_penalty(cls, uncertainty: str) -> float:
        return {"LOW": 0.0, "MEDIUM": 0.15, "HIGH": 0.35, "UNKNOWN": 0.45}.get(str(uncertainty).upper(), 0.45)

    @classmethod
    def _reliability_bonus(cls, reliability: str) -> float:
        return {"STRONG": 0.20, "MODERATE": 0.10, "WEAK": 0.0, "UNKNOWN": -0.10}.get(str(reliability).upper(), -0.10)

    @classmethod
    def rank_candidate(
        cls,
        candidate: Dict[str, Any],
        *,
        uncertainty: str,
        reliability: str,
        resource_pressure: str,
        latency_posture: str,
        cost_posture: str,
    ) -> Dict[str, Any]:
        base = cls._safe_float(candidate.get("score"), 0.0)
        cost = cls._safe_float(candidate.get("cost_usd"), 10**6)
        latency = cls._safe_float(candidate.get("latency_ms"), 10**6)
        score = base
        score += cls._reliability_bonus(reliability)
        score -= cls._uncertainty_penalty(uncertainty)
        if resource_pressure in {"ELEVATED", "CRITICAL"}:
            score -= min(0.25, max(0.0, latency / 10000.0))
        if latency_posture == "SLOW":
            score -= min(0.20, latency / 10000.0)
        if cost_posture == "OVER_BUDGET":
            score -= min(0.20, cost / 10.0)
        return {
            "provider": str(candidate.get("provider") or ""),
            "tool": str(candidate.get("tool") or ""),
            "score": round(score, 6),
            "source_score": round(base, 6),
            "cost_usd": cost,
            "latency_ms": latency,
        }

    @classmethod
    def plan(
        cls,
        *,
        project_id: str,
        context: Dict[str, Any],
        candidates: Iterable[Dict[str, Any]],
        uncertainty: str,
        reliability: str,
        resource_pressure: str,
        latency_posture: str,
        cost_posture: str,
        governance_required: bool = True,
    ) -> Dict[str, Any]:
        cleaned: List[Dict[str, Any]] = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            if not str(candidate.get("provider") or "").strip() or not str(candidate.get("tool") or "").strip():
                continue
            cleaned.append(candidate)
        if not cleaned:
            status = "HOLD"
            routes: List[Dict[str, Any]] = []
        else:
            routes = [
                cls.rank_candidate(
                    c,
                    uncertainty=uncertainty,
                    reliability=reliability,
                    resource_pressure=resource_pressure,
                    latency_posture=latency_posture,
                    cost_posture=cost_posture,
                )
                for c in cleaned
            ]
            routes.sort(key=lambda r: (-r["score"], r["cost_usd"], r["latency_ms"], r["provider"], r["tool"]))
            top = routes[0]
            top_gap = routes[0]["score"] - routes[1]["score"] if len(routes) > 1 else 1.0
            if uncertainty.upper() in {"HIGH", "UNKNOWN"} or reliability.upper() == "UNKNOWN":
                status = "REFINE"
            elif top_gap < 0.05:
                status = "REFINE"
            else:
                status = "RECOMMEND"
        return {
            "status": status,
            "project_id": str(project_id),
            "plan_id": cls.plan_id(project_id, context, cleaned),
            "routes": routes,
            "selected_route": None if not routes else routes[0],
            "decision_basis": {
                "uncertainty": str(uncertainty).upper(),
                "reliability": str(reliability).upper(),
                "resource_pressure": str(resource_pressure).upper(),
                "latency_posture": str(latency_posture).upper(),
                "cost_posture": str(cost_posture).upper(),
            },
            "governance_required": bool(governance_required),
            "external_action_executed": False,
            "governance_authority": "POLICY_AND_GOVERNANCE_REMAIN_AUTHORITATIVE",
        }
