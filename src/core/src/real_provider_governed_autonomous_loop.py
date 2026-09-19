"""O46-S60 real-provider governed autonomous loop.

Connects the O46 prototype to the existing real model/search providers while
remaining bounded by S58 resource governance. Provider calls are used only for
research/decision/execution synthesis; no external side effect is performed.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Callable, Mapping
import json, hashlib

from .multi_dimensional_resource_governor import MultiDimensionalResourceGovernor, ResourceLimits
from .live_providers import model_provider, search_provider, provider_configuration_status


def _hash(value: Any) -> str:
    return hashlib.sha256(repr(value).encode('utf-8')).hexdigest()


def _extract_json(text: str) -> dict[str, Any] | None:
    text = (text or '').strip()
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except Exception:
        return None


@dataclass(frozen=True)
class RealProviderCycle:
    cycle_index: int
    evidence_refs: tuple[str, ...]
    evidence_hash: str
    decision: str
    execution_status: str
    trace_id: str
    next_decision: str
    provider_calls: int
    budget_status: str

@dataclass(frozen=True)
class RealProviderLoopResult:
    status: str
    cycles: tuple[RealProviderCycle, ...]
    closed_loop: bool
    reentered: bool
    external_action_executed: bool
    memory_write_executed: bool
    execution_triggered_by_reentry: bool


class RealProviderGovernedAutonomousLoop:
    """Two-cycle O46 loop using real providers behind S58 bounds."""
    def __init__(self, *, limits: ResourceLimits | None = None,
                 model_fn: Callable[[str], Mapping[str, Any]] | None = None,
                 search_fn: Callable[[str], Mapping[str, Any]] | None = None) -> None:
        self.model_fn = model_fn or model_provider
        self.search_fn = search_fn or search_provider
        self.governor = MultiDimensionalResourceGovernor(limits or ResourceLimits(
            max_time_ms=30_000, max_provider_calls=8, max_retry_attempts=2,
            max_concurrency=1, max_cycles=2))

    @staticmethod
    def _evidence_refs(payload: Mapping[str, Any]) -> tuple[str, ...]:
        refs=[]
        for idx, item in enumerate(payload.get('results') or []):
            if isinstance(item, Mapping):
                refs.append(str(item.get('url') or item.get('title') or f'provider-result-{idx+1}'))
            else:
                refs.append(f'provider-result-{idx+1}')
        return tuple(refs)

    def _decision(self, topic: str, evidence: Mapping[str, Any], prior: str | None) -> str:
        prompt = json.dumps({
            'task':'Return JSON only with fields decision and rationale.',
            'topic':topic,
            'evidence_refs':list(self._evidence_refs(evidence)),
            'prior_next_decision':prior,
            'constraints':['Do not claim external execution.','Decision must be bounded and evidence-aware.']
        }, ensure_ascii=False)
        response = self.model_fn(prompt)
        parsed = _extract_json(str(response.get('text','')))
        if parsed and parsed.get('decision'):
            return str(parsed['decision'])
        return 'PROCEED_WITH_BOUNDED_VALIDATION'

    def _execution(self, topic: str, decision: str) -> str:
        prompt = json.dumps({
            'task':'Return JSON only with fields status and result.',
            'topic':topic,
            'decision':decision,
            'execution_mode':'BOUNDED_NON_EXTERNAL_SYNTHESIS',
            'constraints':['No network side effects.','No publishing, spending, deleting, messaging, or memory writes.']
        }, ensure_ascii=False)
        response = self.model_fn(prompt)
        parsed = _extract_json(str(response.get('text','')))
        if parsed and str(parsed.get('status','')).upper() in {'SUCCESS','COMPLETE'}:
            return 'SUCCESS'
        return 'INCONCLUSIVE'

    def run(self, *, topic: str = 'O46 real-provider governed loop validation', project_id: str = 'O46-S60') -> RealProviderLoopResult:
        if provider_configuration_status().get('status') != 'CONFIGURED':
            raise RuntimeError('real_provider_configuration_incomplete')
        cycles=[]
        prior_next=None
        for cycle_index in (1,2):
            admission=self.governor.admit(time_ms=1000, provider_calls=3, retry_attempts=0, concurrency=1, cycles=1)
            if not admission.allowed:
                return RealProviderLoopResult('FAIL_CLOSED',tuple(cycles),False,False,False,False,False)
            evidence=dict(self.search_fn(topic))
            refs=self._evidence_refs(evidence)
            evidence_hash=_hash(evidence)
            decision=self._decision(topic,evidence,prior_next)
            status=self._execution(topic,decision)
            trace_id=f'O46-S60-TRACE-{_hash((project_id,cycle_index,evidence_hash,decision))[:16]}'
            next_decision='REENTER_WITH_REFRESHED_REAL_EVIDENCE' if cycle_index==1 else 'STOP_OR_REQUEST_APPROVAL'
            cycles.append(RealProviderCycle(cycle_index,refs,evidence_hash,decision,status,trace_id,next_decision,3,admission.status))
            prior_next=next_decision
        return RealProviderLoopResult('PASS',tuple(cycles),True,True,False,False,False)
