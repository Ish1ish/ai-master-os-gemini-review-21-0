"""Provider reliability primitives: bounded retry, classification, and circuit breaker.

The layer is intentionally side-effect free beyond in-process circuit state. It does
not perform provider calls by itself; callers supply the operation to execute.
"""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional, TypeVar

T = TypeVar("T")


class ProviderRequestError(RuntimeError):
    """Normalized provider transport error preserving HTTP status when available."""

    def __init__(self, message: str, *, status_code: Optional[int] = None, retry_after: Optional[float] = None):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


def _float_env(name: str, default: float, minimum: float = 0.0) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, value)


def _int_env(name: str, default: int, minimum: int = 1) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, value)


@dataclass(frozen=True)
class ProviderReliabilityConfig:
    max_attempts: int = 3
    backoff_s: float = 0.25
    max_backoff_s: float = 2.0
    circuit_failure_threshold: int = 3
    circuit_cooldown_s: float = 30.0

    @classmethod
    def from_env(cls) -> "ProviderReliabilityConfig":
        return cls(
            max_attempts=_int_env("AI_OS_PROVIDER_MAX_ATTEMPTS", 3),
            backoff_s=_float_env("AI_OS_PROVIDER_BACKOFF_S", 0.25),
            max_backoff_s=_float_env("AI_OS_PROVIDER_MAX_BACKOFF_S", 2.0),
            circuit_failure_threshold=_int_env("AI_OS_PROVIDER_CIRCUIT_FAILURE_THRESHOLD", 3),
            circuit_cooldown_s=_float_env("AI_OS_PROVIDER_CIRCUIT_COOLDOWN_S", 30.0),
        )


@dataclass
class _Circuit:
    failures: int = 0
    opened_at: Optional[float] = None

    @property
    def is_open(self) -> bool:
        return self.opened_at is not None


class ProviderCircuitOpenError(ProviderRequestError):
    """Raised when the provider circuit is open and calls are fail-closed."""

    def __init__(self, provider: str):
        super().__init__(f"provider_circuit_open:{provider}")
        self.provider = provider


_CIRCUITS: Dict[str, _Circuit] = {}
_LOCK = threading.RLock()


def reset_provider_reliability_state() -> None:
    with _LOCK:
        _CIRCUITS.clear()


def _circuit_for(provider: str) -> _Circuit:
    with _LOCK:
        return _CIRCUITS.setdefault(provider, _Circuit())


def _is_retryable(exc: BaseException) -> bool:
    status = getattr(exc, "status_code", None)
    if status == 429 or (isinstance(status, int) and 500 <= status <= 599):
        return True
    name = type(exc).__name__.lower()
    text = str(exc).lower()
    retry_tokens = ("timeout", "timed out", "tempor", "connection", "network", "unavailable", "reset")
    return any(token in name or token in text for token in retry_tokens)


def _retry_delay(exc: BaseException, attempt: int, config: ProviderReliabilityConfig) -> float:
    retry_after = getattr(exc, "retry_after", None)
    if retry_after is not None:
        try:
            return min(config.max_backoff_s, max(0.0, float(retry_after)))
        except (TypeError, ValueError):
            pass
    return min(config.max_backoff_s, config.backoff_s * (2 ** max(0, attempt - 1)))


def call_with_provider_reliability(provider: str, operation: Callable[[], T], config: Optional[ProviderReliabilityConfig] = None) -> T:
    cfg = config or ProviderReliabilityConfig.from_env()
    circuit = _circuit_for(provider)
    now = time.monotonic()
    with _LOCK:
        if circuit.is_open:
            if circuit.opened_at is None or (now - circuit.opened_at) < cfg.circuit_cooldown_s:
                raise ProviderCircuitOpenError(provider)
            # Half-open probe: allow exactly this caller to test the provider.
            circuit.opened_at = None

    last_exc: Optional[BaseException] = None
    for attempt in range(1, cfg.max_attempts + 1):
        try:
            result = operation()
            with _LOCK:
                circuit.failures = 0
                circuit.opened_at = None
            return result
        except Exception as exc:  # provider boundary intentionally normalizes exceptions
            last_exc = exc
            retryable = _is_retryable(exc)
            if not retryable:
                raise
            if attempt >= cfg.max_attempts:
                with _LOCK:
                    circuit.failures += 1
                    if circuit.failures >= cfg.circuit_failure_threshold:
                        circuit.opened_at = time.monotonic()
                raise
            time.sleep(_retry_delay(exc, attempt, cfg))

    if last_exc is not None:
        raise last_exc
    raise ProviderRequestError(f"provider_call_failed:{provider}")


def reliability_snapshot() -> dict:
    with _LOCK:
        return {
            name: {
                "failures": state.failures,
                "open": state.is_open,
                "opened_at": state.opened_at,
            }
            for name, state in _CIRCUITS.items()
        }
