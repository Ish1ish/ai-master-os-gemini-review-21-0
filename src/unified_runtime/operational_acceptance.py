"""S16 operational acceptance harness.

Validates the frozen unified runtime at the local/runtime boundary without
claiming an external production deployment. Repeats health/readiness and a
bounded go-live check, then records an operational acceptance result.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .go_live import UnifiedRuntimeGoLiveValidationGate
from .production import UnifiedRuntimeProductionService


class UnifiedRuntimeOperationalAcceptance:
    VERSION = "1.0"

    def __init__(self, workspace_root: str | Path):
        self.root = Path(workspace_root)

    def run(self, *, run_id: str = "UR-OA-001", repeats: int = 2) -> dict[str, Any]:
        if repeats < 1 or repeats > 3:
            return {
                "status": "BLOCKED",
                "gate": "UNIFIED_RUNTIME_OPERATIONAL_ACCEPTANCE",
                "version": self.VERSION,
                "failures": ["invalid_repeat_bound"],
            }

        production = UnifiedRuntimeProductionService(self.root)
        try:
            health = production.health()
            readiness = production.readiness()
            go_live = UnifiedRuntimeGoLiveValidationGate(self.root).run(
                release_run_id=run_id
            )
            cycles = []
            for index in range(repeats):
                cycle = production.run({
                    "run_id": f"{run_id}-C{index + 1}",
                    "project_id": "OPS-ACCEPTANCE",
                    "strategy_id": "A",
                    "intent": "operational_acceptance_probe",
                    "goal": "Validate bounded operational acceptance of the unified runtime.",
                    "audience": "internal_runtime_validation",
                    "constraints": {"external_action": False, "memory_write": False},
                    "requested_language": "en",
                    "risk_tolerance": "standard",
                })
                cycles.append({
                    "status": cycle.get("status"),
                    "persistence": cycle.get("persistence", {}).get("status"),
                    "external_action": cycle.get("external_action"),
                    "memory_write": cycle.get("memory_write"),
                })

            checks = {
                "health_green": health.get("status") == "HEALTHY",
                "readiness_green": readiness.get("status") == "READY",
                "go_live_ready": go_live.get("status") == "READY_FOR_GO_LIVE_VALIDATION",
                "all_cycles_succeeded": all(c["status"] in {"PASS", "SUCCEEDED", "IDEMPOTENT_REPLAY"} for c in cycles),
                "external_action_blocked": all(c["external_action"] is False for c in cycles),
                "memory_write_blocked": all(c["memory_write"] is False for c in cycles),
                "repeat_bound_enforced": True,
            }
            failures = [name for name, ok in checks.items() if not ok]
            return {
                "status": "OPERATIONALLY_ACCEPTED" if not failures else "BLOCKED",
                "gate": "UNIFIED_RUNTIME_OPERATIONAL_ACCEPTANCE",
                "version": self.VERSION,
                "workspace_root": str(self.root),
                "run_id": run_id,
                "checks": checks,
                "failures": failures,
                "health": health,
                "readiness": readiness,
                "go_live": go_live,
                "cycles": cycles,
                "deployment_mode": "NOT_DEPLOYED",
                "external_environment_verified": False,
            }
        finally:
            production.close()
