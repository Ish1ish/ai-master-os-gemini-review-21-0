"""O45-S58 multi-dimensional resource governance.

Provides a deterministic, fail-closed governor over time, provider calls,
retry attempts, concurrency, and closed-loop cycle count. It is deliberately
execution-agnostic: reserving/consuming a resource never executes a tool,
provider, memory write, or external action.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ResourceLimits:
    max_time_ms: int = 30_000
    max_provider_calls: int = 8
    max_retry_attempts: int = 6
    max_concurrency: int = 2
    max_cycles: int = 2

    def validate(self) -> None:
        for name in (
            "max_time_ms",
            "max_provider_calls",
            "max_retry_attempts",
            "max_concurrency",
            "max_cycles",
        ):
            value = int(getattr(self, name))
            if value < 1:
                raise ValueError(f"{name} must be >= 1")


@dataclass(frozen=True)
class ResourceUsage:
    time_ms: int = 0
    provider_calls: int = 0
    retry_attempts: int = 0
    concurrency: int = 0
    cycles: int = 0


@dataclass(frozen=True)
class GovernanceDecision:
    status: str
    reason: str
    usage: ResourceUsage
    limits: ResourceLimits
    exhausted_dimensions: tuple[str, ...] = ()

    @property
    def allowed(self) -> bool:
        return self.status == "ALLOWED"


class MultiDimensionalResourceGovernor:
    """Deterministic resource governor with fail-closed semantics."""

    DIMENSIONS = ("time", "provider_calls", "retry_attempts", "concurrency", "cycles")

    def __init__(self, limits: ResourceLimits | None = None) -> None:
        self.limits = limits or ResourceLimits()
        self.limits.validate()
        self._usage = ResourceUsage()
        self._peak_concurrency = 0
        self._blocked = False
        self._block_reason = ""

    @property
    def usage(self) -> ResourceUsage:
        return self._usage

    @property
    def peak_concurrency(self) -> int:
        return self._peak_concurrency

    @property
    def blocked(self) -> bool:
        return self._blocked

    def _decision(self, status: str, reason: str, exhausted: tuple[str, ...] = ()) -> GovernanceDecision:
        return GovernanceDecision(status, reason, self._usage, self.limits, exhausted)

    def _would_exceed(self, delta: Mapping[str, int]) -> tuple[str, ...]:
        projected = {
            "time": self._usage.time_ms + int(delta.get("time", 0)),
            "provider_calls": self._usage.provider_calls + int(delta.get("provider_calls", 0)),
            "retry_attempts": self._usage.retry_attempts + int(delta.get("retry_attempts", 0)),
            "concurrency": int(delta.get("concurrency", self._usage.concurrency)),
            "cycles": self._usage.cycles + int(delta.get("cycles", 0)),
        }
        limits = {
            "time": self.limits.max_time_ms,
            "provider_calls": self.limits.max_provider_calls,
            "retry_attempts": self.limits.max_retry_attempts,
            "concurrency": self.limits.max_concurrency,
            "cycles": self.limits.max_cycles,
        }
        return tuple(k for k in self.DIMENSIONS if projected[k] > limits[k])

    def admit(
        self,
        *,
        time_ms: int = 0,
        provider_calls: int = 0,
        retry_attempts: int = 0,
        concurrency: int | None = None,
        cycles: int = 0,
    ) -> GovernanceDecision:
        if self._blocked:
            return self._decision("BLOCKED", self._block_reason, (self._block_reason,))
        delta = {
            "time": max(0, int(time_ms)),
            "provider_calls": max(0, int(provider_calls)),
            "retry_attempts": max(0, int(retry_attempts)),
            "concurrency": self._usage.concurrency if concurrency is None else max(0, int(concurrency)),
            "cycles": max(0, int(cycles)),
        }
        exceeded = self._would_exceed(delta)
        if exceeded:
            reason = "RESOURCE_BUDGET_EXCEEDED:" + ",".join(exceeded)
            self._blocked = True
            self._block_reason = reason
            return self._decision("BLOCKED", reason, exceeded)
        self._usage = ResourceUsage(
            time_ms=self._usage.time_ms + delta["time"],
            provider_calls=self._usage.provider_calls + delta["provider_calls"],
            retry_attempts=self._usage.retry_attempts + delta["retry_attempts"],
            concurrency=delta["concurrency"],
            cycles=self._usage.cycles + delta["cycles"],
        )
        self._peak_concurrency = max(self._peak_concurrency, self._usage.concurrency)
        return self._decision("ALLOWED", "RESOURCE_BUDGET_OK")

    def release_concurrency(self, amount: int = 1) -> None:
        if self._blocked:
            return
        amount = max(0, int(amount))
        self._usage = ResourceUsage(
            time_ms=self._usage.time_ms,
            provider_calls=self._usage.provider_calls,
            retry_attempts=self._usage.retry_attempts,
            concurrency=max(0, self._usage.concurrency - amount),
            cycles=self._usage.cycles,
        )

    def snapshot(self) -> GovernanceDecision:
        return self._decision("BLOCKED" if self._blocked else "ALLOWED", self._block_reason or "RESOURCE_SNAPSHOT")

    def reset(self) -> None:
        self._usage = ResourceUsage()
        self._peak_concurrency = 0
        self._blocked = False
        self._block_reason = ""
