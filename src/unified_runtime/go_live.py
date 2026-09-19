"""S15 go-live validation gate for the unified runtime.

Validates that the frozen code/package gate is green and that the runtime
exposes an explicit, fail-closed deployment posture. This module does not
perform deployment and never claims that an external production environment
has been verified.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .release_readiness import UnifiedRuntimeReleaseReadinessGate


class UnifiedRuntimeGoLiveValidationGate:
    VERSION = "1.0"

    def __init__(self, workspace_root: str | Path):
        self.root = Path(workspace_root)

    def run(self, *, release_run_id: str = "UR-GOLIVE-001") -> dict[str, Any]:
        readiness = UnifiedRuntimeReleaseReadinessGate(self.root).run(
            acceptance_run_id=release_run_id
        )
        ready = readiness.get("status") == "READY_FOR_RELEASE"
        posture = {
            "deployment_mode": "NOT_DEPLOYED",
            "external_environment_verified": False,
            "external_action": False,
            "memory_write": False,
        }
        checks = {
            "release_readiness_green": ready,
            "release_manifest_present": bool(readiness.get("manifest_fingerprint")),
            "s13_acceptance_passed": bool(readiness.get("checks", {}).get("s13_acceptance_passed")),
            "external_environment_not_claimed": posture["external_environment_verified"] is False,
            "external_action_blocked": posture["external_action"] is False,
            "memory_write_blocked": posture["memory_write"] is False,
        }
        failures = [k for k, v in checks.items() if not v]
        return {
            "status": "READY_FOR_GO_LIVE_VALIDATION" if not failures else "BLOCKED",
            "gate": "UNIFIED_RUNTIME_GO_LIVE_VALIDATION",
            "version": self.VERSION,
            "workspace_root": str(self.root),
            "checks": checks,
            "failures": failures,
            "readiness": readiness,
            "posture": posture,
            "note": "This gate validates release/go-live posture only; it does not perform or claim external production deployment.",
        }
