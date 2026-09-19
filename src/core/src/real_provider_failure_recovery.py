"""O45-S53 real-provider closed-loop failure injection and recovery.

Injects bounded, deterministic transient provider failures around the already
verified S52 real-provider closed loop. Recovery is local to provider calls;
the closed-loop governance boundaries remain unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .live_providers import model_provider, search_provider, provider_configuration_status
from .real_provider_closed_loop import RealProviderClosedLoopCoordinator, RealProviderClosedLoopResult


ProviderFn = Callable[[str], Mapping[str, Any]]


@dataclass
class InjectionState:
    model_failures: int = 0
    search_failures: int = 0


class TransientFailureInjector:
    """Fail a bounded number of times before delegating to the real provider."""

    def __init__(self, *, model_failures: int = 0, search_failures: int = 0) -> None:
        self.model_remaining = max(0, int(model_failures))
        self.search_remaining = max(0, int(search_failures))
        self.state = InjectionState()

    def model(self, delegate: ProviderFn) -> ProviderFn:
        def wrapped(prompt: str) -> Mapping[str, Any]:
            if self.model_remaining > 0:
                self.model_remaining -= 1
                self.state.model_failures += 1
                raise RuntimeError("s53_injected_transient_model_failure")
            return delegate(prompt)
        return wrapped

    def search(self, delegate: ProviderFn) -> ProviderFn:
        def wrapped(query: str) -> Mapping[str, Any]:
            if self.search_remaining > 0:
                self.search_remaining -= 1
                self.state.search_failures += 1
                raise RuntimeError("s53_injected_transient_search_failure")
            return delegate(query)
        return wrapped


class BoundedProviderRecovery:
    """Retry a provider call up to max_attempts; fail closed after exhaustion."""

    def __init__(self, *, max_attempts: int = 2) -> None:
        if int(max_attempts) < 1:
            raise ValueError("max_attempts must be >= 1")
        self.max_attempts = int(max_attempts)
        self.attempts: dict[str, int] = {"model": 0, "search": 0}

    def wrap(self, kind: str, delegate: ProviderFn) -> ProviderFn:
        if kind not in self.attempts:
            raise ValueError("unsupported provider kind")

        def wrapped(value: str) -> Mapping[str, Any]:
            last_error: Exception | None = None
            for _ in range(self.max_attempts):
                self.attempts[kind] += 1
                try:
                    result = delegate(value)
                    if not isinstance(result, Mapping):
                        raise RuntimeError(f"s53_{kind}_invalid_provider_contract")
                    return result
                except Exception as exc:  # bounded recovery boundary
                    last_error = exc
            raise RuntimeError(f"s53_{kind}_recovery_exhausted") from last_error

        return wrapped


@dataclass(frozen=True)
class FailureRecoveryResult:
    closed_loop: RealProviderClosedLoopResult
    injected_model_failures: int
    injected_search_failures: int
    model_attempts: int
    search_attempts: int
    external_action_executed: bool = False
    memory_write_executed: bool = False


class RealProviderFailureRecoveryCoordinator:
    """Run the S52 real-provider loop with deterministic transient failures."""

    def __init__(
        self,
        *,
        model: ProviderFn | None = None,
        search: ProviderFn | None = None,
        model_failures: int = 1,
        search_failures: int = 1,
        max_attempts: int = 2,
        allow_external_execution: bool = False,
    ) -> None:
        injector = TransientFailureInjector(
            model_failures=model_failures,
            search_failures=search_failures,
        )
        recovery = BoundedProviderRecovery(max_attempts=max_attempts)
        base_model = model or model_provider
        base_search = search or search_provider
        recovered_model = recovery.wrap("model", injector.model(base_model))
        recovered_search = recovery.wrap("search", injector.search(base_search))
        self.injector = injector
        self.recovery = recovery
        self.coordinator = RealProviderClosedLoopCoordinator(
            model=recovered_model,
            search=recovered_search,
            allow_external_execution=allow_external_execution,
        )

    def run(self, *, project_id: str = "P-S53") -> FailureRecoveryResult:
        result = self.coordinator.run_two_cycles(project_id=project_id)
        return FailureRecoveryResult(
            closed_loop=result,
            injected_model_failures=self.injector.state.model_failures,
            injected_search_failures=self.injector.state.search_failures,
            model_attempts=self.recovery.attempts["model"],
            search_attempts=self.recovery.attempts["search"],
            external_action_executed=False,
            memory_write_executed=False,
        )


def validate_s53_provider_configuration() -> Mapping[str, Any]:
    return provider_configuration_status()
