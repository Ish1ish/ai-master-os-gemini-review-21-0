"""S17 deployment/environment validation contract for the unified runtime.

This is the final local gate before a real deployment. It validates that the
frozen workspace exposes the required runtime, release, and operational
surfaces and performs a local smoke probe. It never deploys and never claims
an external environment was verified.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


class UnifiedRuntimeDeploymentValidation:
    VERSION = "1.0"

    REQUIRED_SOURCE = (
        "src/unified_runtime/contract.py",
        "src/unified_runtime/entrypoint.py",
        "src/unified_runtime/production.py",
        "src/unified_runtime/release_readiness.py",
        "src/unified_runtime/go_live.py",
        "src/unified_runtime/operational_acceptance.py",
        "src/unified_runtime/final_gate.py",
    )
    REQUIRED_TESTS = (
        "tests/test_unified_runtime_s13_final_gate.py",
        "tests/test_unified_runtime_s14_release.py",
        "tests/test_unified_runtime_s15_go_live.py",
        "tests/test_unified_runtime_s16_operational.py",
    )

    def __init__(self, workspace_root: str | Path):
        self.root = Path(workspace_root)

    def _present(self, relative_paths: tuple[str, ...]) -> bool:
        return all((self.root / item).is_file() for item in relative_paths)

    def run(self, *, release_identity: str = "S17-GOLIVE-001") -> dict[str, Any]:
        source_complete = self._present(self.REQUIRED_SOURCE)
        tests_complete = self._present(self.REQUIRED_TESTS)
        manifest_present = (self.root / "release_manifest.json").is_file()
        workspace_present = self.root.is_dir()

        health = {"status": "UNKNOWN"}
        readiness = {"status": "UNKNOWN"}
        smoke = {"status": "NOT_RUN"}

        try:
            from .production import UnifiedRuntimeProductionService
            service = UnifiedRuntimeProductionService(self.root / ".s17_validation")
            health = service.health()
            readiness = service.readiness()
            smoke = {
                "status": "PASS",
                "health": health.get("status"),
                "readiness": readiness.get("status"),
            }
        except Exception as exc:
            smoke = {
                "status": "BLOCKED",
                "reason": "local_runtime_smoke_failed",
                "error_type": type(exc).__name__,
            }

        posture = {
            "deployment_mode": "NOT_DEPLOYED",
            "external_environment_verified": False,
            "external_action": False,
            "memory_write": False,
        }
        checks = {
            "workspace_present": workspace_present,
            "source_surface_complete": source_complete,
            "test_surface_complete": tests_complete,
            "release_manifest_present": manifest_present,
            "local_health_green": health.get("status") == "HEALTHY",
            "local_readiness_green": readiness.get("status") == "READY",
            "local_smoke_passed": smoke.get("status") == "PASS",
            "external_environment_not_claimed": posture["external_environment_verified"] is False,
            "external_action_blocked": posture["external_action"] is False,
            "memory_write_blocked": posture["memory_write"] is False,
        }
        failures = [name for name, ok in checks.items() if not ok]
        return {
            "status": "READY_FOR_DEPLOYMENT_VALIDATION" if not failures else "BLOCKED",
            "gate": "UNIFIED_RUNTIME_DEPLOYMENT_VALIDATION",
            "version": self.VERSION,
            "release_identity": release_identity,
            "workspace_root": str(self.root),
            "checks": checks,
            "failures": failures,
            "health": health,
            "readiness": readiness,
            "smoke": smoke,
            "posture": posture,
            "note": "Local deployment validation only. No external deployment or environment verification is performed or claimed.",
        }
