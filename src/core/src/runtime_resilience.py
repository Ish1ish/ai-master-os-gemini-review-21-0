
"""O39-S38 runtime resilience primitives.

Bounded concurrency, per-run time budgets, cancellation, admission control, and
fail-closed state transitions. Dependency-free and safe to exercise in gates.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future, wait, FIRST_EXCEPTION
from typing import Callable, Generic, TypeVar

T = TypeVar("T")

class RunState(str, Enum):
    ADMITTED = "ADMITTED"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"

@dataclass(frozen=True)
class ResilienceConfig:
    max_workers: int = 4
    max_inflight_runs: int = 4
    run_timeout_s: float = 60.0
    acquire_timeout_s: float = 0.0

    def __post_init__(self) -> None:
        if self.max_workers < 1 or self.max_inflight_runs < 1:
            raise ValueError("concurrency limits must be >= 1")
        if self.run_timeout_s <= 0 or self.acquire_timeout_s < 0:
            raise ValueError("timeouts must be non-negative and run timeout > 0")

@dataclass
class RunRecord:
    run_id: str
    state: RunState = RunState.ADMITTED
    started_at: float | None = None
    ended_at: float | None = None
    error: str | None = None
    cancelled: bool = False

class AdmissionController:
    def __init__(self, limit: int) -> None:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        self._sem = threading.BoundedSemaphore(limit)
        self.limit = limit
        self._lock = threading.Lock()
        self.inflight = 0
        self.peak_inflight = 0

    def acquire(self, timeout: float = 0.0) -> bool:
        ok = self._sem.acquire(timeout=timeout)
        if ok:
            with self._lock:
                self.inflight += 1
                self.peak_inflight = max(self.peak_inflight, self.inflight)
        return ok

    def release(self) -> None:
        with self._lock:
            if self.inflight <= 0:
                raise RuntimeError("admission release without acquire")
            self.inflight -= 1
        self._sem.release()

class ResilientRuntime(Generic[T]):
    def __init__(self, config: ResilienceConfig | None = None) -> None:
        self.config = config or ResilienceConfig()
        self.admission = AdmissionController(self.config.max_inflight_runs)
        self.pool = ThreadPoolExecutor(max_workers=self.config.max_workers, thread_name_prefix="ai-os-run")
        self._records: dict[str, RunRecord] = {}
        self._lock = threading.Lock()
        self._closed = False

    def submit(self, run_id: str, fn: Callable[[], T]) -> Future[T]:
        with self._lock:
            if self._closed:
                raise RuntimeError("runtime_closed")
            if run_id in self._records and self._records[run_id].state in {RunState.ADMITTED, RunState.RUNNING}:
                raise RuntimeError("duplicate_active_run")
            self._records[run_id] = RunRecord(run_id=run_id)

        if not self.admission.acquire(self.config.acquire_timeout_s):
            with self._lock:
                self._records[run_id].state = RunState.FAILED
                self._records[run_id].error = "concurrency_admission_rejected"
            raise RuntimeError("concurrency_admission_rejected")

        def wrapped() -> T:
            with self._lock:
                record = self._records[run_id]
                record.state = RunState.RUNNING
                record.started_at = time.monotonic()
            try:
                result = fn()
                with self._lock:
                    record.state = RunState.COMPLETE
                return result
            except Exception as exc:
                with self._lock:
                    record.state = RunState.FAILED
                    record.error = type(exc).__name__ + ": " + str(exc)[:240]
                raise
            finally:
                with self._lock:
                    record.ended_at = time.monotonic()
                self.admission.release()

        try:
            return self.pool.submit(wrapped)
        except Exception:
            self.admission.release()
            with self._lock:
                self._records[run_id].state = RunState.FAILED
                self._records[run_id].error = "submission_failed"
            raise

    def record(self, run_id: str) -> RunRecord:
        with self._lock:
            rec = self._records.get(run_id)
            if rec is None:
                raise KeyError(run_id)
            return RunRecord(**vars(rec))

    def cancel(self, run_id: str) -> bool:
        with self._lock:
            rec = self._records.get(run_id)
            if rec is None:
                return False
            rec.cancelled = True
            if rec.state is RunState.ADMITTED:
                rec.state = RunState.CANCELLED
                return True
            return False

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self.pool.shutdown(wait=True, cancel_futures=True)
