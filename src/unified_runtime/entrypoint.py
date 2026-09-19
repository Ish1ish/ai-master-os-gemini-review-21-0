"""S11 Unified Runtime Entrypoint.

Provides one stable, request-shaped host entrypoint over the S10 real runtime.
The entrypoint performs deterministic validation, preserves the canonical
identity fields, and fails closed on malformed requests or runtime errors.
It does not enable external actions or automatic memory writes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from .integrated_runtime import RealUnifiedRuntime


@dataclass(frozen=True)
class UnifiedRuntimeRequest:
    run_id: str
    project_id: str
    strategy_id: str
    intent: str
    goal: str = ""
    audience: str = ""
    constraints: Mapping[str, Any] = field(default_factory=dict)
    requested_language: str = "en"
    risk_tolerance: str = "standard"
    evidence: Optional[Mapping[str, Any]] = None
    execution_contract: Optional[Mapping[str, Any]] = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "UnifiedRuntimeRequest":
        required = ("run_id", "project_id", "strategy_id", "intent")
        missing = [name for name in required if not str(payload.get(name, "")).strip()]
        if missing:
            raise ValueError("missing_required_fields:" + ",".join(missing))

        constraints = payload.get("constraints", {})
        if constraints is None:
            constraints = {}
        if not isinstance(constraints, Mapping):
            raise ValueError("constraints_must_be_mapping")

        evidence = payload.get("evidence")
        if evidence is not None and not isinstance(evidence, Mapping):
            raise ValueError("evidence_must_be_mapping")

        execution_contract = payload.get("execution_contract")
        if execution_contract is not None and not isinstance(execution_contract, Mapping):
            raise ValueError("execution_contract_must_be_mapping")

        return cls(
            run_id=str(payload["run_id"]),
            project_id=str(payload["project_id"]),
            strategy_id=str(payload["strategy_id"]),
            intent=str(payload["intent"]),
            goal=str(payload.get("goal", "")),
            audience=str(payload.get("audience", "")),
            constraints=dict(constraints),
            requested_language=str(payload.get("requested_language", "en")),
            risk_tolerance=str(payload.get("risk_tolerance", "standard")),
            evidence=dict(evidence) if evidence is not None else None,
            execution_contract=dict(execution_contract) if execution_contract is not None else None,
        )


class UnifiedRuntimeEntrypoint:
    '''Stable host boundary with optional governed O45 execution contracts: PATCH_02_O45_UNIFIED_BRIDGE_V1.'''
    """Stable host boundary for the real unified runtime."""

    VERSION = "1.0"

    def __init__(self, persistence_root: str, *, enable_external_actions: bool = False):
        self.runtime = RealUnifiedRuntime(
            persistence_root,
            enable_external_actions=enable_external_actions,
        )

    def register_execution_tool(self, tool_name: str, handler, *, version: str = "v1", enabled: bool = True, retry_safe: bool = False):
        return self.runtime.register_execution_tool(
            tool_name,
            handler,
            version=version,
            enabled=enabled,
            retry_safe=retry_safe,
        )

    def close(self) -> None:
        self.runtime.close()

    def run(self, request: UnifiedRuntimeRequest | Mapping[str, Any], principal: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
        try:
            normalized = (
                request
                if isinstance(request, UnifiedRuntimeRequest)
                else UnifiedRuntimeRequest.from_mapping(request)
            )
            result = self.runtime.run(
                run_id=normalized.run_id,
                project_id=normalized.project_id,
                strategy_id=normalized.strategy_id,
                intent=normalized.intent,
                goal=normalized.goal,
                audience=normalized.audience,
                constraints=normalized.constraints,
                requested_language=normalized.requested_language,
                risk_tolerance=normalized.risk_tolerance,
                evidence=normalized.evidence,
                principal=principal,
                execution_contract=normalized.execution_contract,
            )
            result = dict(result)
            result["entrypoint"] = {
                "version": self.VERSION,
                "request_mode": "UNIFIED_RUNTIME_ENTRYPOINT",
                "external_action_capability": False,
            }
            if principal is not None:
                result["entrypoint"]["principal_id"] = principal.get("principal")
            return result
        except (TypeError, ValueError) as exc:
            return {
                "status": "BLOCKED",
                "reason": str(exc),
                "entrypoint": {
                    "version": self.VERSION,
                    "request_mode": "UNIFIED_RUNTIME_ENTRYPOINT",
                    "external_action_capability": False,
                },
                "external_action": False,
                "governance_mutation": False,
                "memory_write": False,
            }
        except Exception as exc:  # Preserved to maintain existing S11 contract test_runtime_failure_fails_closed
            return {
                "status": "BLOCKED",
                "reason": "runtime_error",
                "error_type": type(exc).__name__,
                "entrypoint": {
                    "version": self.VERSION,
                    "request_mode": "UNIFIED_RUNTIME_ENTRYPOINT",
                    "external_action_capability": False,
                },
                "external_action": False,
                "governance_mutation": False,
                "memory_write": False,
            }
