"""Bridge from Unified Runtime S1 to the existing UnifiedDecisionIntelligence engine.

The bridge keeps the existing UDI implementation authoritative for route ranking and
decision status. It only adapts S1 request/context into UDI.plan inputs and normalizes
the result back to the S1 DECISION stage shape.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from core.src.unified_decision_intelligence import UnifiedDecisionIntelligence


def _candidate_from_request(request: Any, understand_data: Dict[str, Any], route_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates = route_data.get("candidates")
    if isinstance(candidates, list):
        return [c for c in candidates if isinstance(c, dict)]

    candidate_provider = route_data.get("candidate_provider")
    if callable(candidate_provider):
        provided = candidate_provider(request, understand_data)
        if isinstance(provided, Iterable) and not isinstance(provided, (str, bytes, dict)):
            return [c for c in provided if isinstance(c, dict)]

    # S1's default route remains deterministic and advisory.
    # A single candidate is enough to let UDI produce a concrete plan without
    # inventing providers/tools that were not supplied by the caller.
    return [{
        "provider": str(route_data.get("provider") or "unified-runtime"),
        "tool": str(route_data.get("tool") or "decision-intelligence"),
        "score": float(route_data.get("score", 0.0) or 0.0),
        "cost_usd": float(route_data.get("cost_usd", 0.0) or 0.0),
        "latency_ms": float(route_data.get("latency_ms", 0.0) or 0.0),
    }]


def build_udi_decision_adapter():
    """Return a S1-compatible decision adapter backed by existing UDI.plan()."""

    def decide(request: Any, understand_data: Dict[str, Any], route_data: Dict[str, Any]) -> Dict[str, Any]:
        context = {
            "intent": request.intent.strip(),
            "goal": request.goal.strip(),
            "audience": request.audience.strip(),
            "requested_language": request.requested_language,
            "risk_tolerance": request.risk_tolerance,
            "constraints": dict(request.constraints),
            "context_refs": list(request.context_refs),
            "understanding": dict(understand_data),
            "route": {
                key: value for key, value in route_data.items()
                if key != "candidate_provider" and not callable(value)
            },
        }

        candidates = _candidate_from_request(request, understand_data, route_data)

        raw = UnifiedDecisionIntelligence.plan(
            project_id=request.project_id,
            context=context,
            candidates=candidates,
            uncertainty=str(route_data.get("uncertainty", "LOW")),
            reliability=str(route_data.get("reliability", "STRONG")),
            resource_pressure=str(route_data.get("resource_pressure", "NORMAL")),
            latency_posture=str(route_data.get("latency_posture", "NORMAL")),
            cost_posture=str(route_data.get("cost_posture", "WITHIN_BUDGET")),
            governance_required=bool(route_data.get("governance_required", True)),
        )

        selected = raw.get("selected_route")
        return {
            "status": str(raw.get("status") or "HOLD"),
            "decision_engine": "UnifiedDecisionIntelligence",
            "plan_id": raw.get("plan_id"),
            "recommendation": selected,
            "selected_route": selected,
            "routes": list(raw.get("routes") or []),
            "decision_basis": dict(raw.get("decision_basis") or {}),
            "governance_required": bool(raw.get("governance_required", True)),
            "governance_authority": raw.get("governance_authority"),
            "external_action": False,
            "external_action_executed": bool(raw.get("external_action_executed", False)),
        }

    return decide
