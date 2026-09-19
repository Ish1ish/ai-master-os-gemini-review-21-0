"""Unified End-to-End Runtime S1: Intent -> Understand -> Route -> Decision.

S1 is deliberately side-effect free. It coordinates existing intelligence through
small adapters and records stage results in the Unified Runtime Contract shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Mapping, Optional

STAGES = ("INTENT", "UNDERSTAND", "ROUTE", "EVIDENCE", "DECISION",
          "EVALUATION", "GOVERNANCE", "EXECUTION", "OUTCOME",
          "FEEDBACK", "LEARNING", "ADAPTATION", "NEXT_DECISION")


@dataclass(frozen=True)
class S1Input:
    project_id: str
    intent: str
    goal: str = ""
    audience: str = ""
    constraints: Mapping[str, Any] = field(default_factory=dict)
    requested_language: str = "en"
    risk_tolerance: str = "standard"
    permissions: Mapping[str, Any] = field(default_factory=dict)
    context_refs: tuple[str, ...] = ()


@dataclass
class StageResult:
    stage: str
    status: str
    data: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""


@dataclass
class S1Result:
    run_id: str
    trace_id: str
    stages: Dict[str, StageResult]
    next_stage: str
    terminal: bool = False

    def as_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "trace_id": self.trace_id,
            "stages": {
                key: {
                    "stage": value.stage,
                    "status": value.status,
                    "data": value.data,
                    "reason": value.reason,
                }
                for key, value in self.stages.items()
            },
            "next_stage": self.next_stage,
            "terminal": self.terminal,
        }


def _stable_id(prefix: str, project_id: str, intent: str) -> str:
    import hashlib
    raw = f"{project_id}|{intent}".encode("utf-8")
    return f"{prefix}-{hashlib.sha256(raw).hexdigest()[:20].upper()}"


def _ok(stage: str, data: Dict[str, Any]) -> StageResult:
    return StageResult(stage=stage, status="SUCCEEDED", data=data)


def build_s1_runtime(
    *,
    understand: Optional[Callable[[S1Input], Dict[str, Any]]] = None,
    route: Optional[Callable[[S1Input, Dict[str, Any]], Dict[str, Any]]] = None,
    decision: Optional[
        Callable[[S1Input, Dict[str, Any], Dict[str, Any]], Dict[str, Any]]
    ] = None,
) -> Callable[[S1Input], S1Result]:

    def run(request: S1Input) -> S1Result:
        run_id = _stable_id("UR", request.project_id, request.intent)
        trace_id = _stable_id("TRC", request.project_id, request.intent)
        stages: Dict[str, StageResult] = {}

        # INTENT is deterministic and has no external side effects.
        intent_data = {
            "intent_id": _stable_id("INT", request.project_id, request.intent),
            "project_id": request.project_id,
            "statement": request.intent.strip(),
            "goal": request.goal.strip(),
            "audience": request.audience.strip(),
            "constraints": dict(request.constraints),
            "requested_language": request.requested_language,
            "risk_tolerance": request.risk_tolerance,
            "context_refs": list(request.context_refs),
        }
        if not intent_data["statement"] or not request.project_id.strip():
            stages["INTENT"] = StageResult(
                "INTENT", "BLOCKED", reason="project_id and intent are required"
            )
            return S1Result(run_id, trace_id, stages, "INTENT", True)
        stages["INTENT"] = _ok("INTENT", intent_data)

        understand_data = (
            understand(request)
            if understand is not None
            else {
                "normalized_goal": request.goal.strip() or request.intent.strip(),
                "problem_statement": request.intent.strip(),
                "evidence_boundary": "NO_EXTERNAL_EVIDENCE_COLLECTED_IN_S1",
            }
        )
        if not isinstance(understand_data, dict):
            stages["UNDERSTAND"] = StageResult(
                "UNDERSTAND", "FAILED", reason="understand adapter must return a dict"
            )
            return S1Result(run_id, trace_id, stages, "UNDERSTAND", True)
        stages["UNDERSTAND"] = _ok("UNDERSTAND", understand_data)

        route_data = (
            route(request, understand_data)
            if route is not None
            else {
                "route_type": "DECISION_INTELLIGENCE",
                "route_mode": "ADVISORY",
                "external_action": False,
            }
        )
        if not isinstance(route_data, dict) or not route_data.get("route_type"):
            stages["ROUTE"] = StageResult(
                "ROUTE", "BLOCKED", reason="route adapter must provide route_type"
            )
            return S1Result(run_id, trace_id, stages, "ROUTE", True)
        stages["ROUTE"] = _ok("ROUTE", route_data)

        decision_data = (
            decision(request, understand_data, route_data)
            if decision is not None
            else {
                "status": "DEFERRED_TO_EXISTING_DECISION_ENGINE",
                "recommendation": None,
                "evidence_refs": list(request.context_refs),
                "external_action": False,
                "governance_required": False,
            }
        )
        if not isinstance(decision_data, dict):
            stages["DECISION"] = StageResult(
                "DECISION", "FAILED", reason="decision adapter must return a dict"
            )
            return S1Result(run_id, trace_id, stages, "DECISION", True)
        stages["DECISION"] = _ok("DECISION", decision_data)

        return S1Result(run_id, trace_id, stages, "EVIDENCE", False)

    return run
