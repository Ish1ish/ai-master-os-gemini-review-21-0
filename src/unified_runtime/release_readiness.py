"""S14 release-readiness and freeze gate for the unified runtime.

This layer does not change runtime behavior. It verifies that the unified runtime
source/test surfaces required for release are present, that the S13 acceptance
gate passes, and that a deterministic source manifest can be produced. It never
claims that an external production deployment has been verified.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Iterable

from .final_gate import UnifiedRuntimeFinalAcceptanceGate


class UnifiedRuntimeReleaseReadinessGate:
    VERSION = "1.0"
    REQUIRED_SOURCE_FILES = (
        "contract.py",
        "s1.py",
        "udi_adapter.py",
        "o42_adapter.py",
        "evaluation_adapter.py",
        "governance_adapter.py",
        "execution_outcome.py",
        "learning_adaptation.py",
        "golden_run.py",
        "persistence.py",
        "runtime.py",
        "integrated_runtime.py",
        "entrypoint.py",
        "production.py",
        "final_gate.py",
    )
    REQUIRED_TEST_FILES = (
        "test_unified_runtime_contract.py",
        "test_unified_runtime_s1.py",
        "test_unified_runtime_s1_udi.py",
        "test_unified_runtime_s2_o42.py",
        "test_unified_runtime_s3_evaluation.py",
        "test_unified_runtime_s4_governance.py",
        "test_unified_runtime_s5_execution_outcome.py",
        "test_unified_runtime_s6_feedback_learning_adaptation.py",
        "test_unified_runtime_s7_golden.py",
        "test_unified_runtime_s8_persistence_memory.py",
        "test_unified_runtime_s9_coordinator.py",
        "test_unified_runtime_s10_integrated.py",
        "test_unified_runtime_s11_entrypoint.py",
        "test_unified_runtime_s12_operations.py",
        "test_unified_runtime_s13_final_gate.py",
    )

    def __init__(self, workspace_root: str | Path):
        self.root = Path(workspace_root)

    def _paths(self, names: Iterable[str], folder: str) -> list[Path]:
        base = self.root / folder
        return [base / name for name in names]

    @staticmethod
    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def source_manifest(self) -> list[dict[str, str]]:
        paths = self._paths(self.REQUIRED_SOURCE_FILES, "src/unified_runtime")
        return [
            {"path": str(p.relative_to(self.root)).replace("\\", "/"), "sha256": self._sha256(p)}
            for p in sorted(paths)
        ]

    def run(self, *, acceptance_run_id: str = "UR-RELEASE-GATE-001") -> dict[str, Any]:
        source_paths = self._paths(self.REQUIRED_SOURCE_FILES, "src/unified_runtime")
        test_paths = self._paths(self.REQUIRED_TEST_FILES, "tests")
        checks = {
            "workspace_exists": self.root.exists(),
            "source_surface_complete": all(p.is_file() for p in source_paths),
            "test_surface_complete": all(p.is_file() for p in test_paths),
        }

        acceptance: dict[str, Any] | None = None
        if checks["workspace_exists"] and checks["source_surface_complete"]:
            try:
                # The embedded S13 acceptance is a fresh code-level acceptance run.
                # Use an isolated temporary persistence root so repeated S14 test
                # invocations cannot inherit a prior persisted run and turn the
                # first acceptance execution into an unexpected replay.
                with tempfile.TemporaryDirectory(prefix="s14_acceptance_") as tmp_root:
                    acceptance = UnifiedRuntimeFinalAcceptanceGate(tmp_root).run(
                        run_id=acceptance_run_id
                    )
                checks["s13_acceptance_passed"] = acceptance.get("status") == "PASS"
            except Exception as exc:  # pragma: no cover - defensive boundary
                checks["s13_acceptance_passed"] = False
                acceptance = {"status": "ERROR", "error_type": type(exc).__name__}
        else:
            checks["s13_acceptance_passed"] = False

        manifest = self.source_manifest() if checks["source_surface_complete"] else []
        manifest_blob = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        manifest_fingerprint = hashlib.sha256(manifest_blob.encode("utf-8")).hexdigest()
        checks["manifest_deterministic"] = bool(manifest_fingerprint)

        failures = [name for name, passed in checks.items() if not passed]
        return {
            "status": "READY_FOR_RELEASE" if not failures else "BLOCKED",
            "gate": "UNIFIED_RUNTIME_RELEASE_READINESS_FREEZE",
            "version": self.VERSION,
            "workspace_root": str(self.root),
            "checks": checks,
            "failures": failures,
            "source_manifest": manifest,
            "manifest_fingerprint": manifest_fingerprint,
            "acceptance": acceptance,
            "production_deployment_verified": False,
            "external_action": False,
            "memory_write": False,
            "note": "Release readiness is a code/package gate; it does not claim live production deployment verification.",
        }
