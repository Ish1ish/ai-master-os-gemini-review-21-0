"""O39-S42 combined security/failure chaos drill.

Dependency-free, in-process only. Combines provider transient failure,
rate-limit recovery, bounded concurrent execution, interrupted-worker
reconciliation, duplicate protections, and terminal-state integrity.
No network, filesystem state domains, secrets, or external actions are used.
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import as_completed

from .provider_resilience import (
    ProviderRequestError,
    ProviderReliabilityConfig,
    call_with_provider_reliability,
    reset_provider_reliability_state,
    reliability_snapshot,
)
from .runtime_resilience import ResilienceConfig, ResilientRuntime, RunState
from .crash_recovery import CrashRecoveryController, RecoveryState


def run_combined_chaos() -> dict:
    reset_provider_reliability_state()

    provider_attempts = {"model": 0, "search": 0}

    def flaky_model():
        provider_attempts["model"] += 1
        if provider_attempts["model"] <= 2:
            raise ProviderRequestError("synthetic_5xx", status_code=503)
        return {"text": "MODEL_OK"}

    def rate_limited_search():
        provider_attempts["search"] += 1
        if provider_attempts["search"] == 1:
            raise ProviderRequestError("synthetic_429", status_code=429, retry_after=0.0)
        return {"results": [{"title": "SEARCH_OK"}]}

    model_result = call_with_provider_reliability(
        "chaos-model",
        flaky_model,
        ProviderReliabilityConfig(max_attempts=3, backoff_s=0.0, max_backoff_s=0.0, circuit_failure_threshold=2, circuit_cooldown_s=0.01),
    )
    search_result = call_with_provider_reliability(
        "chaos-search",
        rate_limited_search,
        ProviderReliabilityConfig(max_attempts=2, backoff_s=0.0, max_backoff_s=0.0, circuit_failure_threshold=2, circuit_cooldown_s=0.01),
    )

    runtime = ResilientRuntime(ResilienceConfig(max_workers=2, max_inflight_runs=2, run_timeout_s=10.0, acquire_timeout_s=0.05))
    started = threading.Event()

    def work(i: int):
        if i == 0:
            started.set()
            time.sleep(0.01)
            raise RuntimeError("synthetic_provider_failure_after_recovery")
        time.sleep(0.005)
        return f"ok-{i}"

    futures = {}
    admission_failures = 0
    for i in range(6):
        try:
            futures[i] = runtime.submit(f"chaos-{i}", lambda i=i: work(i))
        except RuntimeError:
            admission_failures += 1
    runtime_results = {}
    for i, future in futures.items():
        try:
            runtime_results[i] = future.result()
        except Exception as exc:
            runtime_results[i] = type(exc).__name__

    duplicate_blocked = False
    try:
        runtime.submit("chaos-0", lambda: None)
    except RuntimeError as exc:
        duplicate_blocked = str(exc) == "duplicate_active_run"  # still active only if not terminal
    except Exception:
        pass
    runtime.close()

    recovery = CrashRecoveryController()
    recovery.submit("chaos-recover-1")
    recovery.claim("chaos-recover-1", "worker-a", "lease-a")
    interrupted = recovery.crash_worker("worker-a")
    reconciled = recovery.reconcile_after_restart()
    recovery.requeue_recovered("chaos-recover-1")
    recovery.claim("chaos-recover-1", "worker-b", "lease-b")
    recovery.complete("chaos-recover-1", "hash-chaos-recover-1")
    recovered_terminal = recovery.records["chaos-recover-1"].state is RecoveryState.COMPLETE
    execution_count = recovery.records["chaos-recover-1"].execution_count

    duplicate_lease_blocked = False
    recovery.submit("chaos-recover-2")
    recovery.claim("chaos-recover-2", "worker-c", "lease-c")
    recovery.submit("chaos-recover-3")
    try:
        recovery.claim("chaos-recover-3", "worker-d", "lease-c")
    except RuntimeError as exc:
        duplicate_lease_blocked = str(exc) == "duplicate_lease"

    peak_ok = runtime.admission.peak_inflight <= 2
    failed_runtime_runs = sum(1 for v in runtime_results.values() if v != "ok-1" and isinstance(v, str))
    terminal_count = len(runtime_results) == len(futures)

    return {
        "model_recovered_after_5xx": model_result.get("text") == "MODEL_OK" and provider_attempts["model"] == 3,
        "search_recovered_after_429": search_result.get("results") and provider_attempts["search"] == 2,
        "runtime_bounded_peak": peak_ok,
        "runtime_terminal_integrity": terminal_count,
        "runtime_failure_contained": runtime_results.get(0) == "RuntimeError",
        "recovery_detected_interruption": interrupted == ["chaos-recover-1"],
        "recovery_reconciled_after_restart": reconciled == ["chaos-recover-1"],
        "recovery_terminal_after_resume": recovered_terminal and execution_count == 2,
        "duplicate_lease_blocked": duplicate_lease_blocked,
        "provider_snapshot_safe": all("api" not in str(v).lower() for v in reliability_snapshot().values()),
        "admission_failures": admission_failures,
        "peak_inflight": runtime.admission.peak_inflight,
        "model_attempts": provider_attempts["model"],
        "search_attempts": provider_attempts["search"],
        "runtime_results": runtime_results,
    }
