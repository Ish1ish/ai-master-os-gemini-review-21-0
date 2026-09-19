"""O46 prototype: governed autonomous loop composition boundary.

Prototype scope:
Research/evidence -> decision -> governance/resource admission -> bounded local
execution callback -> outcome -> learning signal -> persisted trace -> re-entry.

This layer is intentionally a composition boundary. It does not grant external
execution, approval, memory writes, or autonomous publication/spending.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Callable, Mapping
import hashlib

from .multi_dimensional_resource_governor import MultiDimensionalResourceGovernor, ResourceLimits

LocalAction = Callable[[Mapping[str, Any]], Mapping[str, Any]]
ResearchFn = Callable[[str], Mapping[str, Any]]


def _hash(value: Any) -> str:
    return hashlib.sha256(repr(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class O46Decision:
    decision_id: str
    statement: str
    evidence_refs: tuple[str, ...]
    next_action: str


@dataclass(frozen=True)
class O46Cycle:
    cycle_index: int
    decision: O46Decision
    outcome_status: str
    trace_id: str
    learning_signal: str
    next_decision: str
    evidence_hash: str
    resources: Mapping[str, Any]


@dataclass(frozen=True)
class O46LoopResult:
    status: str
    cycles: tuple[O46Cycle, ...]
    closed_loop: bool
    reentered: bool
    external_action_executed: bool
    memory_write_executed: bool
    execution_triggered: bool


class GovernedAutonomousLoopPrototype:
    """Bounded O46 prototype using existing O45 governance contracts."""

    def __init__(
        self,
        *,
        research: ResearchFn | None = None,
        action: LocalAction | None = None,
        limits: ResourceLimits | None = None,
        allow_external_execution: bool = False,
    ) -> None:
        self.research = research or self._default_research
        self.action = action or self._default_action
        self.allow_external_execution = bool(allow_external_execution)
        self.governor = MultiDimensionalResourceGovernor(
            limits or ResourceLimits(
                max_time_ms=10_000,
                max_provider_calls=8,
                max_retry_attempts=4,
                max_concurrency=1,
                max_cycles=2,
            )
        )
        self._trace: list[O46Cycle] = []
        self._seen_idempotency: set[str] = set()

    @staticmethod
    def _default_research(topic: str) -> Mapping[str, Any]:
        return {
            "topic": topic,
            "evidence": [
                {"ref": "O46-LOCAL-EVIDENCE-1", "claim": "Prototype evidence placeholder"}
            ],
        }

    @staticmethod
    def _default_action(payload: Mapping[str, Any]) -> Mapping[str, Any]:
        # Local deterministic action only; never touches network, files, memory, or UI.
        return {"status": "SUCCESS", "action": payload.get("action", "bounded_local_step")}

    def _decision(self, cycle_index: int, evidence: Mapping[str, Any]) -> O46Decision:
        refs = tuple(str(item.get("ref")) for item in evidence.get("evidence", []) if item.get("ref"))
        statement = "Proceed with bounded next step using current evidence."
        if cycle_index > 1:
            statement = "Reassess using prior outcome trace and refreshed evidence."
        return O46Decision(
            decision_id=f"O46-D{cycle_index}",
            statement=statement,
            evidence_refs=refs,
            next_action="bounded_local_step",
        )

    def run(self, *, project_id: str = "O46-PROTOTYPE", topic: str = "governed loop validation") -> O46LoopResult:
        cycles: list[O46Cycle] = []
        for cycle_index in (1, 2):
            admitted = self.governor.admit(
                time_ms=100,
                provider_calls=1,
                retry_attempts=0,
                concurrency=1,
                cycles=1,
            )
            if not admitted.allowed:
                return O46LoopResult(
                    status="FAIL_CLOSED",
                    cycles=tuple(cycles),
                    closed_loop=False,
                    reentered=False,
                    external_action_executed=False,
                    memory_write_executed=False,
                    execution_triggered=False,
                )

            evidence = dict(self.research(topic))
            if cycle_index > 1:
                prior = cycles[-1]
                evidence["prior_trace_id"] = prior.trace_id
                evidence["prior_next_decision"] = prior.next_decision

            evidence_hash = _hash(evidence)
            decision = self._decision(cycle_index, evidence)
            idem = f"O46-{project_id}-C{cycle_index}"
            if idem in self._seen_idempotency:
                return O46LoopResult("FAIL_CLOSED", tuple(cycles), False, False, False, False, False)
            self._seen_idempotency.add(idem)

            result = self.action({
                "project_id": project_id,
                "cycle_index": cycle_index,
                "decision": asdict(decision),
                "evidence_hash": evidence_hash,
                "external_allowed": False,
            })
            outcome = str(result.get("status", "INCONCLUSIVE"))
            learning = (
                "bounded_step_success_supports_next_cycle"
                if outcome == "SUCCESS"
                else "outcome_requires_reassessment"
            )
            trace_id = f"O46-TRACE-{_hash((project_id, cycle_index, evidence_hash))[:16]}"
            next_decision = "REENTER_WITH_REFRESHED_EVIDENCE" if cycle_index == 1 else "STOP_OR_REQUEST_APPROVAL"
            cycles.append(
                O46Cycle(
                    cycle_index=cycle_index,
                    decision=decision,
                    outcome_status=outcome,
                    trace_id=trace_id,
                    learning_signal=learning,
                    next_decision=next_decision,
                    evidence_hash=evidence_hash,
                    resources={"usage": asdict(self.governor.usage), "peak_concurrency": self.governor.peak_concurrency},
                )
            )

        return O46LoopResult(
            status="PASS",
            cycles=tuple(cycles),
            closed_loop=len(cycles) == 2,
            reentered=cycles[1].decision.decision_id == "O46-D2",
            external_action_executed=False,
            memory_write_executed=False,
            execution_triggered=False,
        )

    def trace_snapshot(self) -> tuple[O46Cycle, ...]:
        return tuple(self._trace)
