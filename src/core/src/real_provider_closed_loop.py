"""O45-S52 real-provider closed-loop validation.

Uses the existing live provider adapters as real evidence inputs and then
runs the verified S51 closed-loop composition. Provider calls never grant
external execution, memory writes, or production approval.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .closed_loop_integration import ClosedLoopResult, FullClosedLoopCoordinator
from .live_providers import model_provider, provider_configuration_status, search_provider


ProviderModel = Callable[[str], Mapping[str, Any]]
ProviderSearch = Callable[[str], Mapping[str, Any]]


def _sha256_text(value: Any) -> str:
    text = str(value or "").encode("utf-8")
    return hashlib.sha256(text).hexdigest()


@dataclass(frozen=True)
class ProviderEvidence:
    model_hash: str
    search_hash: str
    search_result_count: int


@dataclass(frozen=True)
class RealProviderClosedLoopResult:
    provider_evidence: ProviderEvidence
    closed_loop: ClosedLoopResult
    external_action_executed: bool = False
    memory_write_executed: bool = False


class RealProviderClosedLoopCoordinator:
    """Validate real providers as evidence inputs to the verified S51 loop."""

    def __init__(
        self,
        *,
        model: ProviderModel | None = None,
        search: ProviderSearch | None = None,
        allow_external_execution: bool = False,
    ) -> None:
        self.model = model or model_provider
        self.search = search or search_provider
        self.closed_loop = FullClosedLoopCoordinator(
            allow_external_execution=allow_external_execution
        )

    def collect_provider_evidence(self, *, topic: str = "AI workflow automation for small businesses") -> ProviderEvidence:
        model_result = self.model(
            "Return a concise internal staging validation response. "
            "Do not request or perform any external action. Topic: " + topic
        )
        if not isinstance(model_result, Mapping):
            raise RuntimeError("real_model_provider_invalid_contract")
        model_text = model_result.get("text")
        if not isinstance(model_text, str) or not model_text.strip():
            raise RuntimeError("real_model_provider_missing_text")

        search_result = self.search(topic + " customer workflow automation")
        if not isinstance(search_result, Mapping):
            raise RuntimeError("real_search_provider_invalid_contract")
        rows = search_result.get("results")
        if not isinstance(rows, list) or not rows:
            raise RuntimeError("real_search_provider_missing_results")

        return ProviderEvidence(
            model_hash=_sha256_text(model_text),
            search_hash=_sha256_text(rows),
            search_result_count=len(rows),
        )

    def run_two_cycles(self, *, project_id: str = "P-S52") -> RealProviderClosedLoopResult:
        evidence = self.collect_provider_evidence()
        refs = (
            "REAL-MODEL-" + evidence.model_hash[:16],
            "REAL-SEARCH-" + evidence.search_hash[:16],
        )
        closed_loop = self.closed_loop.run_cycle(
            project_id=project_id,
            action_id="A-S52-1",
            idempotency_key="S52-CYCLE-1",
            payload={"cycle": 1, "provider_evidence": True},
            evidence_refs=refs,
        )
        # Re-run provider collection before the second decision cycle. This
        # proves that a fresh live-provider observation can feed the loop
        # again without changing its governance boundaries.
        second_evidence = self.collect_provider_evidence()
        refs2 = (
            "REAL-MODEL-" + second_evidence.model_hash[:16],
            "REAL-SEARCH-" + second_evidence.search_hash[:16],
            "REENTRY-FROM-" + closed_loop.reentry.loop_id[:16],
        )
        second = self.closed_loop.run_cycle(
            project_id=project_id,
            action_id="A-S52-2",
            idempotency_key="S52-CYCLE-2",
            payload={"cycle": 2, "source_reentry": closed_loop.reentry.loop_id, "provider_evidence": True},
            evidence_refs=refs2,
        )
        result = ClosedLoopResult(
            cycles=(closed_loop, second),
            final_next_decision=second.next_decision,
            trace_ids=(closed_loop.trace_id, second.trace_id),
            reentry_ids=(closed_loop.reentry.loop_id, second.reentry.loop_id),
            execution_triggered=False,
            external_action_executed=False,
            memory_write_executed=False,
        )
        return RealProviderClosedLoopResult(
            provider_evidence=evidence,
            closed_loop=result,
            external_action_executed=False,
            memory_write_executed=False,
        )


def validate_real_provider_configuration() -> Mapping[str, Any]:
    return provider_configuration_status()
