"""S12 productionization and operations facade for the unified runtime.

Adds a deterministic operational boundary around S11:
health/readiness, counters, bounded retry, persistence recovery, and explicit
operational status. This layer does not grant external-action capability and
does not auto-commit memory proposals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .entrypoint import UnifiedRuntimeEntrypoint


@dataclass
class RuntimeMetrics:
    total_runs: int = 0
    successful_runs: int = 0
    blocked_runs: int = 0
    replayed_runs: int = 0
    runtime_errors: int = 0
    recoveries: int = 0
    last_run_id: str | None = None
    _recent_statuses: list[str] = field(default_factory=list)

    def record(self, result: Mapping[str, Any]) -> None:
        self.total_runs += 1
        self.last_run_id = str(result.get("run_id") or "") or self.last_run_id
        status = str(result.get("status") or "UNKNOWN")
        self._recent_statuses.append(status)
        self._recent_statuses = self._recent_statuses[-10:]
        if status == "PASS":
            self.successful_runs += 1
        elif status == "BLOCKED":
            self.blocked_runs += 1
            if result.get("reason") == "runtime_error":
                self.runtime_errors += 1
        persistence = result.get("persistence")
        if isinstance(persistence, Mapping) and persistence.get("status") == "IDEMPOTENT_REPLAY":
            self.replayed_runs += 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "blocked_runs": self.blocked_runs,
            "replayed_runs": self.replayed_runs,
            "runtime_errors": self.runtime_errors,
            "recoveries": self.recoveries,
            "last_run_id": self.last_run_id,
            "recent_statuses": list(self._recent_statuses),
        }


class UnifiedRuntimeProductionService:
    VERSION = "1.0"

    def __init__(self, persistence_root: str | Path):
        self.persistence_root = Path(persistence_root)
        self.persistence_root.mkdir(parents=True, exist_ok=True)
        self.entrypoint = UnifiedRuntimeEntrypoint(str(self.persistence_root))
        self.metrics = RuntimeMetrics()

    def health(self) -> dict[str, Any]:
        return {
            "status": "HEALTHY",
            "service": "UNIFIED_RUNTIME",
            "version": self.VERSION,
            "runtime_mode": "REAL_ADAPTER_WIRING",
            "external_action_capability": False,
            "memory_write": False,
        }

    def readiness(self) -> dict[str, Any]:
        try:
            probe = self.persistence_root / ".readiness_probe"
            probe.write_text("ready", encoding="utf-8")
            probe.unlink(missing_ok=True)
            trace_path = self.persistence_root / "unified_runs.jsonl"
            return {
                "status": "READY",
                "persistence_root": str(self.persistence_root),
                "trace_store_available": True,
                "external_action_capability": False,
                "memory_write": False,
                "trace_path": str(trace_path),
            }
        except Exception as exc:
            return {
                "status": "NOT_READY",
                "reason": "persistence_unavailable",
                "error_type": type(exc).__name__,
                "external_action_capability": False,
                "memory_write": False,
            }

    def run(self, request: Mapping[str, Any] | Any) -> dict[str, Any]:
        result = self.entrypoint.run(request)
        self.metrics.record(result)
        return result

    def run_with_retry(self, request: Mapping[str, Any] | Any, *, max_attempts: int = 2) -> dict[str, Any]:
        if max_attempts < 1:
            raise ValueError("max_attempts_must_be_positive")
        last = self.run(request)
        attempts = 1
        while last.get("status") == "BLOCKED" and last.get("reason") == "runtime_error" and attempts < max_attempts:
            attempts += 1
            last = self.run(request)
        result = dict(last)
        result["operations"] = {
            "attempts": attempts,
            "retry_policy": "BOUNDED_RUNTIME_ERROR_ONLY",
            "recovered": attempts > 1 and result.get("status") == "PASS",
        }
        return result

    def recover_run(self, run_id: str, project_id: str) -> dict[str, Any]:
        if not str(run_id).strip() or not str(project_id).strip():
            raise ValueError("run_id_and_project_id_are_required")
        record = self.entrypoint.runtime.persistence.get(run_id, project_id)
        if record is None:
            return {
                "status": "NOT_FOUND",
                "run_id": run_id,
                "project_id": project_id,
                "recovered": False,
            }
        self.metrics.recoveries += 1
        return {
            "status": "RECOVERED_FROM_PERSISTENCE",
            "run_id": run_id,
            "project_id": project_id,
            "fingerprint": record.get("fingerprint"),
            "recovered": True,
            "memory_write": False,
            "external_action": False,
        }

    def operational_snapshot(self) -> dict[str, Any]:
        health = self.health()
        readiness = self.readiness()
        return {
            "service": health["service"],
            "version": self.VERSION,
            "health": health["status"],
            "readiness": readiness["status"],
            "metrics": self.metrics.as_dict(),
            "external_action_capability": False,
            "memory_write": False,
        }
