"""O39-S41 crash/restart/interrupted-run recovery primitives.

Dependency-free, isolated recovery model used by release gates. It models a
single durable run record, an ownership lease, crash interruption, restart
reconciliation, and duplicate-execution protection without touching live
application state.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RecoveryState(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    RECOVERED = "RECOVERED"


@dataclass
class DurableRun:
    run_id: str
    state: RecoveryState = RecoveryState.QUEUED
    worker_id: str | None = None
    lease_id: str | None = None
    execution_count: int = 0
    result_hash: str | None = None


class CrashRecoveryController:
    def __init__(self) -> None:
        self.records: dict[str, DurableRun] = {}
        self.active_leases: dict[str, str] = {}
        self._closed = False

    def submit(self, run_id: str) -> DurableRun:
        if self._closed:
            raise RuntimeError("recovery_controller_closed")
        if run_id in self.records and self.records[run_id].state in {
            RecoveryState.QUEUED,
            RecoveryState.RUNNING,
        }:
            raise RuntimeError("duplicate_active_run")
        self.records[run_id] = DurableRun(run_id=run_id)
        return self.records[run_id]

    def claim(self, run_id: str, worker_id: str, lease_id: str) -> DurableRun:
        rec = self.records[run_id]
        if rec.state is not RecoveryState.QUEUED:
            raise RuntimeError("run_not_queuable")
        if lease_id in self.active_leases:
            raise RuntimeError("duplicate_lease")
        rec.state = RecoveryState.RUNNING
        rec.worker_id = worker_id
        rec.lease_id = lease_id
        rec.execution_count += 1
        self.active_leases[lease_id] = run_id
        return rec

    def crash_worker(self, worker_id: str) -> list[str]:
        interrupted = []
        for rec in self.records.values():
            if rec.state is RecoveryState.RUNNING and rec.worker_id == worker_id:
                if rec.lease_id:
                    self.active_leases.pop(rec.lease_id, None)
                interrupted.append(rec.run_id)
        return interrupted

    def reconcile_after_restart(self) -> list[str]:
        recovered = []
        for rec in self.records.values():
            if rec.state is RecoveryState.RUNNING and rec.lease_id not in self.active_leases:
                rec.state = RecoveryState.RECOVERED
                recovered.append(rec.run_id)
        return recovered

    def requeue_recovered(self, run_id: str) -> None:
        rec = self.records[run_id]
        if rec.state is not RecoveryState.RECOVERED:
            raise RuntimeError("run_not_recovered")
        rec.state = RecoveryState.QUEUED
        rec.worker_id = None
        rec.lease_id = None

    def complete(self, run_id: str, result_hash: str) -> None:
        rec = self.records[run_id]
        if rec.state is not RecoveryState.RUNNING:
            raise RuntimeError("run_not_running")
        if rec.lease_id:
            self.active_leases.pop(rec.lease_id, None)
        rec.state = RecoveryState.COMPLETE
        rec.result_hash = result_hash
        rec.worker_id = None
        rec.lease_id = None

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
