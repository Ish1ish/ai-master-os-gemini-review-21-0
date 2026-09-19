"""O39-S39 controlled end-to-end concurrency/load validation harness.

Dependency-free harness for validating the runtime admission/concurrency boundary
with a service-shaped execute callable, duplicate protection, sustained parallel
completion, and terminal-state integrity.
"""
from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Callable, Iterable

from .runtime_resilience import ResilientRuntime, ResilienceConfig, RunState


@dataclass(frozen=True)
class LoadResult:
    submitted: int
    completed: int
    failed: int
    peak_inflight: int
    duplicate_blocked: bool
    terminal_integrity: bool
    elapsed_s: float


def run_controlled_load(
    execute: Callable[[str], str] | None = None,
    *,
    count: int = 12,
    concurrency: int = 4,
) -> LoadResult:
    if count < 1 or concurrency < 1:
        raise ValueError("count and concurrency must be >= 1")

    active = 0
    peak = 0
    lock = threading.Lock()

    def default_execute(run_id: str) -> str:
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        try:
            time.sleep(0.015)
            return run_id
        finally:
            with lock:
                active -= 1

    fn = execute or default_execute
    runtime = ResilientRuntime(
        ResilienceConfig(max_workers=concurrency, max_inflight_runs=concurrency, acquire_timeout_s=2.0)
    )
    start = time.monotonic()
    futures = [runtime.submit(f"load-{i}", lambda i=i: fn(f"load-{i}")) for i in range(count)]
    values = [f.result(timeout=5) for f in futures]

    duplicate_blocked = False
    release = threading.Event()
    first = runtime.submit("duplicate-probe", lambda: (release.wait(2), "ok")[1])
    try:
        runtime.submit("duplicate-probe", lambda: "bad")
    except RuntimeError as exc:
        duplicate_blocked = str(exc) == "duplicate_active_run"
    finally:
        release.set()
        first.result(timeout=3)

    records = [runtime.record(f"load-{i}") for i in range(count)]
    terminal_integrity = all(
        rec.state in {RunState.COMPLETE, RunState.FAILED, RunState.CANCELLED, RunState.TIMED_OUT}
        and rec.ended_at is not None
        for rec in records
    )
    runtime.close()
    elapsed = time.monotonic() - start
    completed = sum(v.startswith("load-") for v in values)
    return LoadResult(
        submitted=count,
        completed=completed,
        failed=count - completed,
        peak_inflight=runtime.admission.peak_inflight,
        duplicate_blocked=duplicate_blocked,
        terminal_integrity=terminal_integrity,
        elapsed_s=elapsed,
    )
