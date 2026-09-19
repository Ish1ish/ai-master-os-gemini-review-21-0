"""S13 production golden run and final acceptance gate.

This gate exercises the productionized unified runtime as an acceptance
scenario rather than changing runtime behavior. It verifies health/readiness,
a canonical PASS journey, deterministic replay, persistence recovery,
operational metrics, canonical stage count, and safety boundaries.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .production import UnifiedRuntimeProductionService


class UnifiedRuntimeFinalAcceptanceGate:
    VERSION = "1.0"
    EXPECTED_STAGE_COUNT = 13

    def __init__(self, persistence_root: str | Path):
        self.service = UnifiedRuntimeProductionService(persistence_root)

    @staticmethod
    def _request(run_id: str, project_id: str = "demo", strategy_id: str = "STRAT-A") -> dict[str, Any]:
        return {
            "run_id": run_id,
            "project_id": project_id,
            "strategy_id": strategy_id,
            "intent": "Validate a low-cost AI workflow",
            "goal": "Prove a bounded next step",
            "audience": "Egypt SMB founders",
            "requested_language": "en",
            "risk_tolerance": "standard",
        }

    def run(self, *, run_id: str = "UR-FINAL-GOLDEN-001") -> dict[str, Any]:
        baseline_metrics = self.service.metrics.as_dict()
        health = self.service.health()
        readiness = self.service.readiness()
        first = self.service.run(self._request(run_id))
        replay = self.service.run(self._request(run_id))
        recovered = self.service.recover_run(run_id, "demo")
        snapshot = self.service.operational_snapshot()

        failures: list[str] = []
        checks = {
            "health": health.get("status") == "HEALTHY",
            "readiness": readiness.get("status") == "READY",
            "golden_run_pass": first.get("status") == "PASS",
            "canonical_stage_count": first.get("stage_count") == self.EXPECTED_STAGE_COUNT,
            "replay": replay.get("persistence", {}).get("status") == "IDEMPOTENT_REPLAY",
            "recovery": recovered.get("status") == "RECOVERED_FROM_PERSISTENCE",
            "external_action_blocked": first.get("external_action") is False,
            "memory_write_blocked": first.get("memory_write") is False,
            "snapshot_healthy": snapshot.get("health") == "HEALTHY",
            "snapshot_ready": snapshot.get("readiness") == "READY",
        }
        failures.extend(name for name, passed in checks.items() if not passed)

        metrics = snapshot.get("metrics", {})
        checks["metrics_total"] = (metrics.get("total_runs", 0) - baseline_metrics.get("total_runs", 0)) == 2
        checks["metrics_replayed"] = (metrics.get("replayed_runs", 0) - baseline_metrics.get("replayed_runs", 0)) == 1
        failures.extend(name for name, passed in checks.items() if not passed and name not in failures)

        return {
            "status": "PASS" if not failures else "BLOCKED",
            "gate": "PRODUCTION_GOLDEN_RUN_FINAL_ACCEPTANCE",
            "version": self.VERSION,
            "run_id": run_id,
            "checks": checks,
            "failures": failures,
            "first_run": first,
            "replay": replay,
            "recovery": recovered,
            "snapshot": snapshot,
            "external_action": False,
            "memory_write": False,
            "production_deployment_verified": False,
            "note": "Code-level acceptance is not a substitute for real deployment verification.",
        }
